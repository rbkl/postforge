# GitHub Actions Guide

## What is GitHub Actions?

**GitHub Actions** is a CI/CD (Continuous Integration/Continuous Deployment) platform built into GitHub. It automates tasks like:

- ✅ **Testing** your code automatically when you push changes
- ✅ **Linting** (checking code quality and style)
- ✅ **Building** your application
- ✅ **Deploying** to production
- ✅ **Running security scans**
- ✅ **Sending notifications**

Think of it as a robot that watches your code and automatically runs checks/tasks whenever you make changes.

## How It Works

1. **You push code** to GitHub
2. **GitHub Actions detects** the push (or pull request)
3. **It runs workflows** defined in `.github/workflows/` folder
4. **You see results** in the "Actions" tab on GitHub

## What I've Set Up For You

I've created a basic CI/CD workflow (`.github/workflows/ci.yml`) that:

### ✅ **Runs Tests**
- Sets up Python 3.12
- Installs dependencies
- Runs database migrations
- Checks Django configuration

### ✅ **Checks Code Quality**
- Runs `flake8` (Python linter)
- Checks code formatting with `black`

### ✅ **When It Runs**
- On every push to `main` or `master` branch
- On every pull request to `main` or `master`

## Viewing GitHub Actions

1. Go to your GitHub repository: `https://github.com/rbkl/postforge`
2. Click the **"Actions"** tab
3. You'll see all workflow runs
4. Click on a run to see detailed logs

## Workflow Status Badges

You can add a badge to your README to show CI status:

```markdown
![CI](https://github.com/rbkl/postforge/workflows/CI%2FCD%20Pipeline/badge.svg)
```

## Common Use Cases

### 1. **Automated Testing**
Every time you push code, GitHub Actions runs your tests to make sure nothing broke.

### 2. **Code Quality Checks**
Automatically checks if your code follows style guidelines.

### 3. **Deployment**
You can set up GitHub Actions to automatically deploy to Railway/Render when you push to `main`.

### 4. **Security Scanning**
Automatically scans for vulnerabilities in your dependencies.

## Example: Adding Deployment

If you want GitHub Actions to automatically deploy to Railway when you push to `main`, you could add:

```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - name: Deploy to Railway
      run: |
        # Railway deployment commands
```

## Benefits

1. **Catch bugs early** - Tests run automatically
2. **Consistent quality** - Code is checked every time
3. **Save time** - No manual testing needed
4. **Team confidence** - Everyone knows the code works
5. **Documentation** - Shows what checks are in place

## Cost

- **Free** for public repositories (unlimited)
- **Free** for private repositories (2,000 minutes/month)
- **Paid** plans available for more minutes

## Next Steps

1. **Push the workflow file** - It's already created in `.github/workflows/ci.yml`
2. **Watch it run** - Go to Actions tab after pushing
3. **Customize** - Add more checks as needed (e.g., unit tests, security scans)

## Learn More

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions) - Pre-built actions you can use

---

**TL;DR**: GitHub Actions is like having a robot assistant that automatically tests and checks your code every time you push changes. It's free, built into GitHub, and helps catch problems early.

