FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --omit=dev

# Build-time environment for Next.js public vars
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_FEATURE_INLINE_EDITOR
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_FEATURE_INLINE_EDITOR=${NEXT_PUBLIC_FEATURE_INLINE_EDITOR}

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
