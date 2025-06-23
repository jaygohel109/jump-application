# Jump AI Backend - Render Deployment Guide

This guide will help you deploy your FastAPI backend on Render.

## Prerequisites

1. A Render account (free tier available)
2. Your code pushed to a Git repository (GitHub, GitLab, etc.)
3. Environment variables ready

## Deployment Steps

### Method 1: Using Render Dashboard (Recommended)

1. **Go to Render Dashboard**
   - Visit [render.com](https://render.com)
   - Sign up/Login to your account

2. **Create New Web Service**
   - Click "New +" button
   - Select "Web Service"
   - Connect your Git repository

3. **Configure the Service**
   - **Name**: `jump-app-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (or choose paid plan)

4. **Set Environment Variables**
   Click "Environment" tab and add these variables:

   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=https://your-render-domain.onrender.com/auth/google/callback
   
   HUBSPOT_CLIENT_ID=your_hubspot_client_id
   HUBSPOT_CLIENT_SECRET=your_hubspot_client_secret
   HUBSPOT_REDIRECT_URI=https://your-render-domain.onrender.com/auth/hubspot/callback
   
   OPENAI_API_KEY=your_openai_api_key
   FRONTEND_URL=https://your-frontend-domain.com
   
   POSTGRES_URL=your_postgres_connection_string
   
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   
   APP_SECRET=your_app_secret_key
   SESSION_SECRET=your_session_secret_key
   
   ALLOWED_ORIGINS=https://your-frontend-domain.com,http://localhost:3000
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app

### Method 2: Using render.yaml (Infrastructure as Code)

1. **Push your code** with the `render.yaml` file to your repository

2. **Go to Render Dashboard**
   - Click "New +" 
   - Select "Blueprint"
   - Connect your repository

3. **Render will automatically**:
   - Read the `render.yaml` configuration
   - Create the service with specified settings
   - You'll still need to add environment variables manually

## Important Configuration Notes

### Environment Variables
- **OAuth Redirect URIs**: Update with your Render domain after deployment
- **Database**: Ensure your database is accessible from Render's servers
- **CORS**: Include your frontend domain in `ALLOWED_ORIGINS`

### Free Tier Limitations
- **Sleep after inactivity**: Free tier services sleep after 15 minutes of inactivity
- **Build time**: Limited build minutes per month
- **Bandwidth**: Limited bandwidth per month

### Performance Optimization
- **Auto-scaling**: Available on paid plans
- **Custom domains**: Available on paid plans
- **SSL**: Automatically provided by Render

## Testing Your Deployment

1. **Health Check**: Visit `https://your-app.onrender.com/health`
2. **Root Endpoint**: Visit `https://your-app.onrender.com/`
3. **API Documentation**: Visit `https://your-app.onrender.com/docs`

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check the build logs in Render dashboard
   - Ensure all dependencies are in `requirements.txt`
   - Verify Python version compatibility

2. **Environment Variables**
   - Double-check all environment variables are set
   - Ensure no typos in variable names
   - Verify sensitive data is correct

3. **Database Connection**
   - Ensure database is accessible from Render
   - Check connection string format
   - Verify database credentials

4. **CORS Issues**
   - Update `ALLOWED_ORIGINS` with your frontend domain
   - Check browser console for CORS errors

### Logs and Monitoring
- View logs in Render dashboard under "Logs" tab
- Monitor performance in "Metrics" tab
- Set up alerts for downtime

## Updating Your Deployment

1. **Automatic Deployments**: Render automatically deploys when you push to your main branch
2. **Manual Deployments**: Use "Manual Deploy" button in dashboard
3. **Rollback**: Use "Rollback" feature if needed

## Cost Optimization

- **Free Tier**: Perfect for development and small projects
- **Paid Plans**: Start at $7/month for always-on services
- **Auto-scaling**: Only pay for what you use

## Security Best Practices

1. **Environment Variables**: Never commit secrets to your repository
2. **HTTPS**: Render provides SSL certificates automatically
3. **CORS**: Restrict origins to your frontend domains only
4. **Database**: Use connection pooling and secure connections

Your FastAPI backend should now be successfully deployed on Render! 🚀 