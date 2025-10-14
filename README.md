# PDF to Flashcards Generator - MVP

A minimal viable product that converts PDF documents into AI-generated flashcards for efficient studying. Upload any PDF and get 10 intelligent flashcards with smooth animations and intuitive navigation.

## 🚀 Features

- **Drag & Drop Upload**: Simple PDF upload with validation (max 10MB)
- **AI-Powered Generation**: Creates 10 high-quality flashcards using OpenAI
- **Interactive Study**: Smooth flip animations and navigation between cards
- **Mobile Responsive**: Works perfectly on all devices
- **No Registration**: Start using immediately, no signup required
- **Real-time Processing**: Live status updates during flashcard generation

## 🛠 Tech Stack

### Frontend
- **Next.js 14** with TypeScript
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **React Dropzone** for file uploads
- **Lucide React** for icons

### Backend
- **FastAPI** with Python
- **SQLite** database for MVP simplicity
- **PyPDF2** for PDF text extraction
- **OpenAI API** for flashcard generation
- **Uvicorn** ASGI server

### Deployment
- **Docker** containerization
- **Docker Compose** for orchestration

## 📋 Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd pdf-flashcards-mvp
```

### 2. Set Up Environment Variables

```bash
cp env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

This will start both the frontend and backend services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### 4. Access the Application

Open your browser and navigate to http://localhost:3000

## 🧪 Manual Setup (Development)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export OPENAI_API_KEY=your_openai_api_key_here

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### YouTube Proxy Troubleshooting

- Ensure `NEXT_PUBLIC_API_URL` points to FastAPI:
  - Local: `http://localhost:8000`
  - Docker Compose: `http://backend:8000`
- Test backend ping:
  - `GET http://localhost:8000/youtube/flashcards/ping` → `{ "ok": true }`
- Test proxy route:
  - `POST http://localhost:3000/api/youtube/flashcards` with `{ "url": "https://youtu.be/VIDEO" }`
- If proxy fails, it will return a descriptive JSON error instead of a generic network error.

## 📁 Project Structure

```
pdf-flashcards-mvp/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── models.py               # Data models
│   ├── pdf_processor.py        # PDF text extraction
│   ├── flashcard_generator.py  # OpenAI integration
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile             # Backend container
│   └── env.example            # Environment template
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Landing page
│   │   ├── flashcards/[id]/
│   │   │   └── page.tsx       # Flashcard viewer
│   │   ├── layout.tsx         # Root layout
│   │   └── globals.css        # Global styles
│   ├── components/
│   │   ├── PDFUpload.tsx      # Upload component
│   │   ├── FlashcardViewer.tsx # Card viewer
│   │   └── ProcessingStatus.tsx # Loading states
│   ├── package.json           # Node dependencies
│   └── Dockerfile             # Frontend container
├── docker-compose.yml         # Container orchestration
├── env.example               # Environment template
└── README.md                 # This file
```

## 🔧 API Endpoints

### Backend API (Port 8000)

- `POST /upload-pdf` - Upload a PDF file
- `POST /generate-flashcards/{pdf_id}` - Start flashcard generation
- `GET /status/{pdf_id}` - Check processing status
- `GET /flashcards/{pdf_id}` - Get generated flashcards

### Example Usage

```bash
# Upload a PDF
curl -X POST "http://localhost:8000/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# Check status
curl "http://localhost:8000/status/your-pdf-id"

# Get flashcards
curl "http://localhost:8000/flashcards/your-pdf-id"
```

## 🎯 How It Works

1. **Upload**: User drags and drops a PDF file (max 10MB)
2. **Validation**: System validates file type and size
3. **Processing**: Background task extracts text and sends to OpenAI
4. **Generation**: AI creates 10 intelligent flashcards
5. **Study**: User reviews cards with flip animations

## 🧪 Testing

### Test Checklist

- [ ] Upload a valid PDF file
- [ ] Verify file size validation (10MB limit)
- [ ] Check file type validation (PDF only)
- [ ] Test flashcard generation process
- [ ] Verify flip animations work
- [ ] Test navigation between cards
- [ ] Check mobile responsiveness
- [ ] Test error handling scenarios

### Manual Testing

1. Upload a small PDF (< 1MB) with clear text content
2. Wait for processing to complete
3. Verify 10 flashcards are generated
4. Test card flipping and navigation
5. Try uploading invalid files to test error handling

## 🚨 Error Handling

The application handles various error scenarios:

- **Invalid file types**: Only PDF files are accepted
- **File size limits**: Maximum 10MB file size
- **PDF parsing failures**: Encrypted or corrupted PDFs
- **OpenAI API errors**: Rate limits, quota exceeded, network issues
- **Processing timeouts**: Long-running operations

## 🔒 Security Considerations

- No user authentication (MVP scope)
- File uploads limited to PDF only
- File size restrictions in place
- No persistent user data storage
- Environment variables for API keys

## 📈 Performance

- Background processing for large PDFs
- Real-time status updates
- Optimized for fast response times
- Efficient database queries
- Minimal resource usage

## 🚀 Deployment

### Production Deployment

1. **Set up environment variables**:
   ```bash
   export OPENAI_API_KEY=your_production_api_key
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Configure reverse proxy** (Nginx recommended):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:3000;
       }
       
       location /api/ {
           proxy_pass http://localhost:8000/;
       }
   }
   ```

### Cloud Deployment

The application can be deployed on:
- **AWS**: ECS, EC2, or Lambda
- **Google Cloud**: Cloud Run or Compute Engine
- **Azure**: Container Instances or App Service
- **DigitalOcean**: Droplets or App Platform
- **Heroku**: Container deployment

## 🤝 Contributing

This is an MVP implementation. For production use, consider:

- Adding user authentication
- Implementing file storage (S3, etc.)
- Adding payment processing
- Building spaced repetition algorithms
- Adding more AI models
- Implementing analytics
- Adding export features

## 📄 License

This project is for educational and MVP purposes. Please ensure you comply with OpenAI's usage policies when using their API.

## 🆘 Troubleshooting

### Common Issues

1. **OpenAI API errors**: Check your API key and billing
2. **Docker build failures**: Ensure Docker is running
3. **Port conflicts**: Change ports in docker-compose.yml
4. **File upload issues**: Check file size and type
5. **Processing failures**: Verify PDF has extractable text

### Debug Mode

Run backend in debug mode:
```bash
cd backend
uvicorn main:app --reload --log-level debug
```

Check logs:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error logs
3. Verify environment setup
4. Test with a simple PDF file

---

**Note**: This is an MVP implementation focused on core functionality. Production deployments should include additional security, monitoring, and scalability considerations.
