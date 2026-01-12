"""
PDF Processing utilities for extracting text and images from academic papers.
"""
import io
import os
import re
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageFilter, ImageDraw
from django.core.files.base import ContentFile


class PDFProcessor:
    """Process academic PDFs to extract text, metadata, and images."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = ""
        self.metadata = {}
        self.images = []
        self.page_images = []  # Full page renders
        
    def extract_all(self) -> Dict:
        """Extract all content from the PDF."""
        try:
            import fitz  # PyMuPDF
            self._extract_with_pymupdf()
        except ImportError:
            self._extract_with_pypdf2()
        
        # Also try to render pages and detect figures
        self._extract_page_figures()
        
        return {
            'text': self.text,
            'metadata': self.metadata,
            'images': self.images
        }
    
    def _extract_with_pymupdf(self):
        """Extract using PyMuPDF (higher quality)."""
        import fitz
        
        doc = fitz.open(self.pdf_path)
        
        # Extract text from all pages
        full_text = []
        for page_num, page in enumerate(doc):
            full_text.append(page.get_text())
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Convert to PIL Image
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    
                    # Filter out very small images (likely icons/logos)
                    if pil_image.width >= 100 and pil_image.height >= 100:
                        self.images.append({
                            'image': pil_image,
                            'page': page_num + 1,
                            'ext': image_ext,
                            'width': pil_image.width,
                            'height': pil_image.height,
                            'is_figure': self._is_likely_figure(pil_image),
                            'caption': '',
                            'source': 'embedded'
                        })
                except Exception as e:
                    print(f"Error extracting image: {e}")
                    continue
        
        self.text = '\n'.join(full_text)
        
        # Extract metadata
        self.metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'page_count': len(doc)
        }
        
        # Try to extract title and abstract from text
        self._parse_arxiv_structure()
        
        doc.close()
    
    def _extract_with_pypdf2(self):
        """Fallback extraction using PyPDF2."""
        from PyPDF2 import PdfReader
        
        reader = PdfReader(self.pdf_path)
        
        full_text = []
        for page in reader.pages:
            full_text.append(page.extract_text())
        
        self.text = '\n'.join(full_text)
        
        # Extract metadata
        if reader.metadata:
            self.metadata = {
                'title': reader.metadata.get('/Title', ''),
                'author': reader.metadata.get('/Author', ''),
                'subject': reader.metadata.get('/Subject', ''),
                'page_count': len(reader.pages)
            }
        
        self._parse_arxiv_structure()
    
    def _parse_arxiv_structure(self):
        """Parse arxiv-style paper structure to extract title and abstract."""
        lines = self.text.split('\n')
        
        # Try to find title (usually first non-empty line or after arxiv identifier)
        title_lines = []
        abstract_started = False
        abstract_lines = []
        
        for i, line in enumerate(lines[:100]):  # Check first 100 lines
            line = line.strip()
            
            if not line:
                continue
            
            # Skip arxiv identifiers
            if re.match(r'^arXiv:', line, re.IGNORECASE):
                continue
            
            # Check for abstract start
            if re.match(r'^abstract', line, re.IGNORECASE):
                abstract_started = True
                # If "Abstract" is followed by content on same line
                if ':' in line:
                    abstract_lines.append(line.split(':', 1)[1].strip())
                continue
            
            # Check for sections that end abstract
            if abstract_started and re.match(r'^(1\.|1 |I\.|Introduction|Keywords)', line, re.IGNORECASE):
                break
            
            if abstract_started:
                abstract_lines.append(line)
            elif not self.metadata.get('title') and i < 10:
                # First few substantial lines are likely the title
                if len(line) > 10 and not re.match(r'^(arXiv|http|www\.)', line, re.IGNORECASE):
                    title_lines.append(line)
                    if len(title_lines) >= 3:  # Limit title to 3 lines
                        break
        
        if title_lines and not self.metadata.get('title'):
            self.metadata['title'] = ' '.join(title_lines)
        
        if abstract_lines:
            self.metadata['abstract'] = ' '.join(abstract_lines)
    
    def _is_likely_figure(self, image: Image.Image) -> bool:
        """Determine if an image is likely a figure/chart vs photo/logo."""
        # Figures tend to have:
        # - White or light backgrounds
        # - Specific aspect ratios
        # - Contain lines/shapes rather than photos
        
        width, height = image.size
        aspect_ratio = width / height if height > 0 else 1
        
        # Figures are usually wider than tall or roughly square
        if 0.5 <= aspect_ratio <= 2.5:
            # Check if image has a lot of white (typical for charts/graphs)
            if image.mode in ('RGB', 'RGBA'):
                # Sample some pixels
                try:
                    small = image.resize((50, 50))
                    pixels = list(small.getdata())
                    white_ish = sum(1 for p in pixels if all(c > 200 for c in p[:3])) / len(pixels)
                    return white_ish > 0.3  # If more than 30% white-ish, likely a figure
                except:
                    pass
            return True
        
        return False
    
    def _extract_page_figures(self):
        """
        Render PDF pages and extract figures/diagrams.
        This captures vector graphics that embedded image extraction misses.
        """
        try:
            from pdf2image import convert_from_path
            import fitz
        except ImportError as e:
            print(f"pdf2image or fitz not available: {e}")
            return
        
        try:
            # Get page count
            doc = fitz.open(self.pdf_path)
            page_count = len(doc)
            
            # Limit to first 20 pages to avoid memory issues
            pages_to_process = min(page_count, 20)
            
            # Render pages at high DPI for quality
            page_images = convert_from_path(
                self.pdf_path,
                dpi=200,  # High quality but not excessive
                first_page=1,
                last_page=pages_to_process,
                fmt='png'
            )
            
            for page_num, page_img in enumerate(page_images, 1):
                # Get text blocks with positions from this page
                page = doc[page_num - 1]
                
                # Find figure regions using text detection
                figure_regions = self._detect_figure_regions(page, page_img)
                
                for region in figure_regions:
                    cropped = self._crop_figure_region(page_img, region)
                    if cropped and self._is_quality_figure(cropped):
                        # Check if we already have a similar image
                        if not self._is_duplicate_image(cropped):
                            self.images.append({
                                'image': cropped,
                                'page': page_num,
                                'ext': 'png',
                                'width': cropped.width,
                                'height': cropped.height,
                                'is_figure': True,
                                'caption': region.get('caption', ''),
                                'source': 'page_render'
                            })
            
            doc.close()
            
        except Exception as e:
            print(f"Error in page figure extraction: {e}")
    
    def _detect_figure_regions(self, page, page_img) -> List[Dict]:
        """
        Detect figure regions on a page by finding figure captions.
        """
        regions = []
        page_width, page_height = page_img.size
        pdf_rect = page.rect
        
        # Scale factors to convert PDF coordinates to image coordinates
        scale_x = page_width / pdf_rect.width
        scale_y = page_height / pdf_rect.height
        
        # Get text blocks
        blocks = page.get_text("dict")["blocks"]
        
        figure_captions = []
        
        for block in blocks:
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    text = "".join([span.get("text", "") for span in line.get("spans", [])])
                    text_lower = text.lower().strip()
                    
                    # Detect figure/table captions
                    if re.match(r'^(figure|fig\.?|table|chart|diagram|graph)\s*\d+', text_lower):
                        bbox = line.get("bbox", block.get("bbox"))
                        if bbox:
                            figure_captions.append({
                                'text': text,
                                'bbox': bbox,
                                'type': 'figure' if 'fig' in text_lower else 'table'
                            })
        
        # For each caption, estimate the figure region (usually above the caption)
        for caption in figure_captions:
            bbox = caption['bbox']
            caption_y = bbox[1] * scale_y  # Top of caption in image coordinates
            caption_x_center = ((bbox[0] + bbox[2]) / 2) * scale_x
            
            # Figure is typically above the caption
            # Estimate region: from ~40% of page height above caption to caption
            figure_top = max(0, caption_y - page_height * 0.35)
            figure_bottom = caption_y + 30 * scale_y  # Include some of caption
            
            # Width: usually centered, spanning ~80% of page or column
            # Try to detect if it's a two-column layout
            if caption_x_center < page_width * 0.4:
                # Left column
                figure_left = 20
                figure_right = page_width * 0.48
            elif caption_x_center > page_width * 0.6:
                # Right column
                figure_left = page_width * 0.52
                figure_right = page_width - 20
            else:
                # Full width
                figure_left = page_width * 0.1
                figure_right = page_width * 0.9
            
            regions.append({
                'bbox': (figure_left, figure_top, figure_right, figure_bottom),
                'caption': caption['text'],
                'type': caption['type']
            })
        
        return regions
    
    def _crop_figure_region(self, page_img: Image.Image, region: Dict) -> Optional[Image.Image]:
        """
        Crop a figure region from a page image with smart boundary detection.
        """
        bbox = region['bbox']
        left, top, right, bottom = [int(x) for x in bbox]
        
        # Ensure valid bounds
        left = max(0, left)
        top = max(0, top)
        right = min(page_img.width, right)
        bottom = min(page_img.height, bottom)
        
        if right <= left or bottom <= top:
            return None
        
        # Crop the region
        cropped = page_img.crop((left, top, right, bottom))
        
        # Try to trim whitespace from edges
        cropped = self._trim_whitespace(cropped)
        
        return cropped
    
    def _trim_whitespace(self, image: Image.Image, threshold: int = 250) -> Image.Image:
        """
        Trim whitespace from image edges.
        """
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get image data
        pixels = image.load()
        width, height = image.size
        
        # Find content boundaries
        top = 0
        bottom = height - 1
        left = 0
        right = width - 1
        
        # Find top edge
        for y in range(height):
            row_has_content = False
            for x in range(width):
                r, g, b = pixels[x, y]
                if r < threshold or g < threshold or b < threshold:
                    row_has_content = True
                    break
            if row_has_content:
                top = y
                break
        
        # Find bottom edge
        for y in range(height - 1, -1, -1):
            row_has_content = False
            for x in range(width):
                r, g, b = pixels[x, y]
                if r < threshold or g < threshold or b < threshold:
                    row_has_content = True
                    break
            if row_has_content:
                bottom = y
                break
        
        # Find left edge
        for x in range(width):
            col_has_content = False
            for y in range(height):
                r, g, b = pixels[x, y]
                if r < threshold or g < threshold or b < threshold:
                    col_has_content = True
                    break
            if col_has_content:
                left = x
                break
        
        # Find right edge
        for x in range(width - 1, -1, -1):
            col_has_content = False
            for y in range(height):
                r, g, b = pixels[x, y]
                if r < threshold or g < threshold or b < threshold:
                    col_has_content = True
                    break
            if col_has_content:
                right = x
                break
        
        # Add small padding
        padding = 10
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        
        if right > left and bottom > top:
            return image.crop((left, top, right, bottom))
        return image
    
    def _is_quality_figure(self, image: Image.Image) -> bool:
        """
        Check if an extracted figure is of good quality (not too small, has content).
        """
        width, height = image.size
        
        # Minimum size requirements
        if width < 150 or height < 100:
            return False
        
        # Check that it's not all white/empty
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        try:
            small = image.resize((50, 50))
            pixels = list(small.getdata())
            
            # Calculate color variance
            non_white = sum(1 for p in pixels if any(c < 240 for c in p[:3]))
            content_ratio = non_white / len(pixels)
            
            # Need at least 10% non-white content
            return content_ratio > 0.10
        except:
            return True
    
    def _is_duplicate_image(self, new_image: Image.Image) -> bool:
        """
        Check if we already have a very similar image.
        """
        if not self.images:
            return False
        
        new_small = new_image.resize((20, 20)).convert('L')
        new_data = list(new_small.getdata())
        
        for existing in self.images:
            try:
                existing_img = existing['image']
                existing_small = existing_img.resize((20, 20)).convert('L')
                existing_data = list(existing_small.getdata())
                
                # Simple pixel difference check
                diff = sum(abs(a - b) for a, b in zip(new_data, existing_data))
                avg_diff = diff / len(new_data)
                
                if avg_diff < 20:  # Very similar
                    return True
            except:
                continue
        
        return False
    
    def get_key_sections(self) -> Dict[str, str]:
        """Extract key sections from the paper."""
        sections = {
            'abstract': self.metadata.get('abstract', ''),
            'introduction': '',
            'conclusion': '',
            'key_findings': ''
        }
        
        text_lower = self.text.lower()
        
        # Find introduction
        intro_patterns = [
            r'(?:^|\n)(?:1\.?\s*)?introduction\s*\n(.*?)(?=\n(?:2\.?\s*)?(?:related|background|method|approach))',
            r'(?:^|\n)introduction\s*\n(.*?)(?=\n\d+\.)'
        ]
        
        for pattern in intro_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                sections['introduction'] = self.text[match.start():match.end()][:2000]
                break
        
        # Find conclusion
        conclusion_patterns = [
            r'(?:^|\n)(?:\d+\.?\s*)?conclusion[s]?\s*\n(.*?)(?=\n(?:acknowledge|reference|appendix|$))',
            r'(?:^|\n)conclusion[s]?\s*\n(.*?)$'
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, text_lower, re.DOTALL | re.IGNORECASE)
            if match:
                sections['conclusion'] = self.text[match.start():match.end()][:2000]
                break
        
        return sections
    
    @staticmethod
    def save_image_to_file(image: Image.Image, filename: str) -> ContentFile:
        """Convert PIL Image to Django ContentFile."""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return ContentFile(buffer.read(), name=filename)

