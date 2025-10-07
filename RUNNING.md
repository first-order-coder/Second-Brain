# PDF-to-Flashcards MVP - Local Development Guide

This guide provides step-by-step instructions for setting up and running the PDF-to-Flashcards MVP locally on your development machine.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone & Project Structure](#clone--project-structure)
3. [Environment Variables](#environment-variables)
4. [Backend Setup](#backend-setup)
5. [Frontend Setup](#frontend-setup)
6. [Optional: Docker Setup](#optional-docker-setup)
7. [Testing the Flow](#testing-the-flow)
8. [Troubleshooting](#troubleshooting)
9. [Cleanup & Maintenance](#cleanup--maintenance)

---

## 🛠 Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Node.js**: Version 18.x or higher
- **Python**: Version 3.11 or higher
- **Git**: Latest version
- **Docker**: Version 20.10+ (optional, for containerized setup)

### Installing Global Tools

#### Node.js & npm
```bash
# Download and install from https://nodejs.org/
# Verify installation:
node --version  # Should show v18.x.x or higher
npm --version   # Should show 9.x.x or higher
```

#### Python & pip
```bash
# Download and install from https://python.org/
# Verify installation:
python --version  # Should show 3.11.x or higher
pip --version     # Should show 23.x.x or higher
```

#### Git
```bash
# Download and install from https://git-scm.com/
# Verify installation:
git --version
```

#### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to "API Keys" section
4. Create a new secret key
5. Copy the key (starts with `sk-`)

---

## 📁 Clone & Project Structure

### Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd pdf-flashcards-mvp

# Verify project structure
ls -la
```

### Expected Directory Layout

```
pdf-flashcards-mvp/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main FastAPI application
│   ├── models.py              # Database models
│   ├── pdf_processor.py       # PDF text extraction
│   ├── flashcard_generator.py # OpenAI integration
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Backend container
│   ├── env.example           # Environment template
│   └── uploads/              # PDF storage directory
├── frontend/                  # Next.js frontend
│   ├── app/                  # Next.js 14 app directory
│   │   ├── page.tsx          # Landing page
│   │   ├── layout.tsx        # Root layout
│   │   ├── globals.css       # Global styles
│   │   └── flashcards/[id]/  # Dynamic flashcard routes
│   ├── components/           # React components
│   │   ├── PDFUpload.tsx     # Upload component
│   │   ├── FlashcardViewer.tsx # Card viewer
│   │   └── ProcessingStatus.tsx # Loading states
│   ├── package.json          # Node dependencies
│   ├── tailwind.config.js    # Tailwind configuration
│   ├── next.config.js        # Next.js configuration
│   └── Dockerfile           # Frontend container
├── docker-compose.yml        # Container orchestration
├── docker-compose.prod.yml   # Production setup
├── env.example              # Environment template
├── README.md                # Project documentation
├── SETUP.md                 # Quick setup guide
└── RUNNING.md               # This file
```

---

## 🔐 Environment Variables

### Backend Environment Setup

Create the backend environment file:

```bash
# Navigate to backend directory
cd backend

# Copy the environment template
cp env.example .env

# Edit the .env file with your OpenAI API key
# Windows (using notepad):
notepad .env

# macOS/Linux (using nano):
nano .env
```

**Backend `.env` file content:**
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

### Frontend Environment Setup (Optional)

The frontend doesn't require environment variables for basic functionality, but you can create one if needed:

```bash
# Navigate to frontend directory
cd ../frontend

# Create frontend environment file (optional)
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local
```

### Security Notes

- **Never commit `.env` files** to version control
- **Keep your OpenAI API key secure** - don't share it publicly
- **Use different keys** for development and production
- **Rotate your API keys** regularly

---

## 🐍 Backend Setup

### Step 1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Verify activation (you should see (venv) in your prompt)
```

### Step 3: Install Dependencies

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Collecting fastapi==0.104.1
Collecting uvicorn[standard]==0.24.0
Collecting python-multipart==0.0.6
Collecting PyPDF2==3.0.1
Collecting openai==1.3.7
Collecting python-dotenv==1.0.0
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
```

### Step 4: Initialize Database

```bash
# The database will be automatically created when you start the server
# SQLite database file: pdf_flashcards.db
```

### Step 5: Start FastAPI Server

```bash
# Start the development server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 6: Verify Backend is Running

Open your browser and visit:
- **API Root**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Alternative Docs**: http://127.0.0.1:8000/redoc

You should see:
- API root returns: `{"message":"PDF to Flashcards API is running"}`
- Interactive API documentation at `/docs`

---

## ⚛️ Frontend Setup

### Step 1: Open New Terminal

Keep the backend running and open a **new terminal window/tab**.

### Step 2: Navigate to Frontend Directory

```bash
cd frontend
```

### Step 3: Install Dependencies

```bash
# Install all dependencies
npm install

# Alternative using yarn:
# yarn install

# Alternative using pnpm:
# pnpm install
```

**Expected output:**
```
added 395 packages, and audited 396 packages in 1m
149 packages are looking for funding
  run `npm fund` for details
```

### Step 4: Start Next.js Development Server

```bash
# Start the development server
npm run dev

# Alternative using yarn:
# yarn dev

# Alternative using pnpm:
# pnpm dev
```

**Expected output:**
```
   ▲ Next.js 14.0.3
   - Local:        http://localhost:3000
   - Network:      http://192.168.1.100:3000

 ✓ Ready in 3.9s
 ○ Compiling / ...
 ✓ Compiled / in 7.7s (1074 modules)
```

### Step 5: Verify Frontend is Running

Open your browser and visit:
- **Frontend App**: http://localhost:3000

You should see:
- Beautiful landing page with "Turn PDFs into Flashcards with AI"
- Drag & drop upload area
- "How it works" section

---

## 🐳 Optional: Docker Setup

If you prefer to run everything in containers, you can use Docker instead of the manual setup above.

### Prerequisites for Docker

```bash
# Verify Docker is installed and running
docker --version
docker-compose --version

# Start Docker Desktop (if on Windows/Mac)
# or start Docker daemon (if on Linux)
```

### Build and Run with Docker

```bash
# Navigate to project root
cd pdf-flashcards-mvp

# Build and start all services
docker-compose up --build

# Run in background (detached mode)
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Services

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000

### Troubleshooting Docker

```bash
# Check running containers
docker-compose ps

# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# View service logs
docker-compose logs backend
docker-compose logs frontend

# Clean up (remove containers and volumes)
docker-compose down -v
docker system prune -f
```

---

## 🧪 Testing the Flow

### Step 1: Upload a PDF

1. Go to http://localhost:3000
2. Drag and drop a PDF file onto the upload area
3. Wait for the upload to complete
4. You should see "Generating flashcards with AI..." message

### Step 2: Monitor Processing

The system will:
1. Upload the PDF to the backend
2. Extract text from the PDF
3. Send content to OpenAI API
4. Generate 10 flashcards
5. Save flashcards to database

### Step 3: View Flashcards

Once processing is complete:
1. You'll be automatically redirected to the flashcards page
2. You can flip cards by clicking them
3. Navigate between cards using prev/next buttons
4. Reset or upload a new PDF

### Step 4: Test API Endpoints

You can also test the API directly:

```bash
# Test API health
curl http://127.0.0.1:8000

# Upload a PDF (replace with actual file path)
curl -X POST "http://127.0.0.1:8000/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"

# Check processing status (replace with actual PDF ID)
curl http://127.0.0.1:8000/status/your-pdf-id

# Get flashcards (replace with actual PDF ID)
curl http://127.0.0.1:8000/flashcards/your-pdf-id
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
# Solution: Make sure virtual environment is activated
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

**Problem**: `Error loading ASGI app. Could not import module "main"`
```bash
# Solution: Make sure you're in the backend directory
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Problem**: `OpenAI API error`
```bash
# Solution: Check your API key in .env file
# Make sure it starts with 'sk-'
# Verify you have OpenAI credits
```

**Problem**: `Port 8000 already in use`
```bash
# Solution: Kill existing process or use different port
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -ti:8000 | xargs kill -9

# Or use different port:
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

#### Frontend Issues

**Problem**: `npm error code ENOENT`
```bash
# Solution: Make sure you're in the frontend directory
cd frontend
npm install
npm run dev
```

**Problem**: `Module not found` errors
```bash
# Solution: Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Problem**: `Upload failed` in browser
```bash
# Solution: Check backend is running
curl http://127.0.0.1:8000

# Check browser console for errors
# Verify API URLs in components match backend address
```

#### PDF Processing Issues

**Problem**: "No text could be extracted from PDF"
```bash
# Solution: Try a different PDF file
# Ensure PDF has selectable text (not just images)
# Avoid encrypted or corrupted PDFs
```

**Problem**: "File size must be less than 10MB"
```bash
# Solution: Compress your PDF or use a smaller file
# Maximum file size is 10MB for the MVP
```

#### Network Issues

**Problem**: Frontend can't connect to backend
```bash
# Solution: Check both services are running
# Verify URLs match (127.0.0.1 vs localhost)
# Check firewall settings
# Try refreshing the browser
```

### Debug Mode

#### Backend Debug
```bash
# Run with debug logging
uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level debug
```

#### Frontend Debug
```bash
# Check browser developer tools (F12)
# Look for errors in Console tab
# Check Network tab for failed requests
```

#### Database Debug
```bash
# Check SQLite database
cd backend
sqlite3 pdf_flashcards.db
.tables
SELECT * FROM pdfs;
SELECT * FROM flashcards;
.quit
```

---

## 🧹 Cleanup & Maintenance

### Reset the Database

```bash
# Stop the backend server (Ctrl+C)
cd backend

# Remove database file
rm pdf_flashcards.db

# Restart server (database will be recreated)
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Clear Uploaded Files

```bash
# Remove all uploaded PDFs
cd backend
rm -rf uploads/*
mkdir uploads
```

### Rotate OpenAI API Key

```bash
# Update .env file with new API key
cd backend
notepad .env  # Windows
nano .env     # macOS/Linux

# Update the OPENAI_API_KEY value
# Restart backend server
```

### Clean Development Environment

```bash
# Remove virtual environment
cd backend
deactivate
rm -rf venv

# Remove node modules
cd ../frontend
rm -rf node_modules package-lock.json

# Remove Docker containers (if used)
docker-compose down -v
docker system prune -f
```

### Performance Monitoring

```bash
# Monitor backend logs
tail -f backend/logs/app.log

# Monitor system resources
# Windows: Task Manager
# macOS: Activity Monitor
# Linux: htop or top

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://127.0.0.1:8000
```

---

## 📚 Additional Resources

### Documentation Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)

### Development Tools

- [Postman](https://www.postman.com/) - API testing
- [Insomnia](https://insomnia.rest/) - API testing alternative
- [VS Code](https://code.visualstudio.com/) - Recommended editor
- [Thunder Client](https://www.thunderclient.com/) - VS Code API extension

### Support

If you encounter issues not covered in this guide:

1. Check the [troubleshooting section](#troubleshooting)
2. Review error logs in browser console and terminal
3. Verify all prerequisites are installed correctly
4. Ensure your OpenAI API key is valid and has credits
5. Try with a simple text-based PDF file

---

## 🎯 Quick Start Summary

For experienced developers who want to get started quickly:

```bash
# 1. Clone and setup
git clone <repo-url> && cd pdf-flashcards-mvp

# 2. Backend
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp env.example .env  # Add your OpenAI API key
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 4. Test
# Visit http://localhost:3000 and upload a PDF
```

**That's it! Your PDF-to-Flashcards MVP should be running locally.** 🎉
