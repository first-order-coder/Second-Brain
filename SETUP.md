# Quick Setup Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Docker and Docker Compose installed
- OpenAI API key

### Step 1: Get Your OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)

### Step 2: Set Up Environment
```bash
# Clone the repository
git clone <repository-url>
cd pdf-flashcards-mvp

# Copy environment template
cp env.example .env

# Edit .env file and add your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here
```

### Step 3: Run the Application
```bash
# Start both frontend and backend
docker-compose up --build

# Wait for both services to start (about 2-3 minutes)
# You'll see logs from both services
```

### Step 4: Access the App
- Open your browser
- Go to http://localhost:3000
- Upload a PDF file
- Wait for processing
- Study your flashcards!

## 🧪 Test with Sample PDF

1. Find any PDF document with text content
2. Make sure it's under 10MB
3. Upload it through the web interface
4. Wait for AI processing (usually 10-30 seconds)
5. Start studying!

## 🔧 Troubleshooting

### Common Issues

**"Connection refused" errors:**
```bash
# Make sure both services are running
docker-compose ps

# Restart if needed
docker-compose down
docker-compose up --build
```

**"OpenAI API error":**
- Check your API key in `.env` file
- Ensure you have OpenAI credits
- Verify the key is valid at platform.openai.com

**"File upload failed":**
- Check file size (must be under 10MB)
- Ensure file is a PDF
- Try a different PDF file

**"No flashcards generated":**
- PDF might be encrypted or corrupted
- PDF might not have extractable text
- Try a simple text-based PDF

### Reset Everything
```bash
# Stop all services
docker-compose down

# Remove all containers and volumes
docker-compose down -v

# Remove images
docker rmi pdf-flashcards-mvp_backend pdf-flashcards-mvp_frontend

# Start fresh
docker-compose up --build
```

## 📱 Mobile Testing

The app is mobile-responsive! Test on your phone:
1. Find your computer's IP address
2. Access http://YOUR_IP:3000 from your phone
3. Upload and study flashcards on mobile

## 🎯 Next Steps

Once you have it running:
1. Try different types of PDFs
2. Test the flashcard navigation
3. Check mobile responsiveness
4. Explore the code structure

## 🆘 Need Help?

1. Check the full README.md for detailed documentation
2. Review error logs: `docker-compose logs`
3. Ensure all prerequisites are installed
4. Verify your OpenAI API key works

Happy studying! 🎓
