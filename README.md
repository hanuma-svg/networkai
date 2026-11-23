# NetworkAI: Intelligent Networking Co-Pilot

NetworkAI is an autonomous, AI-powered professional networking platform with:
- **`/backend`**: Python 3.12 service powered by FastAPI, LangGraph, Supabase (`pgvector`), Inngest, and Gemini embeddings.
- **`/frontend`**: Mobile-first Progressive Web App (PWA) with Next.js App Router, Tailwind CSS, Supabase Realtime cloud sync, and Web Share Target.
- **`/extension`**: Manifest V3 Chrome Extension Side Panel for desktop LinkedIn profile analysis and 1-tap approvals.
- **`/supabase`**: Schema with `pgvector` embedding table (`contacts`), `interactions`, and `action_queue` with strict 300-char LinkedIn constraints.

---

## Production Deployment Runbook

### Step 1: Push Code to GitHub

1. Initialize git in the root folder (if not already done) and stage all files:
   ```bash
   git init
   git add .
   git commit -m "feat: complete NetworkAI monorepo with Inngest, PWA, and Extension"
   ```
2. Create a new repository on GitHub (e.g. `your-username/networkai`) and push:
   ```bash
   git remote add origin https://github.com/your-username/networkai.git
   git branch -M main
   git push -u origin main
   ```

---

### Step 2: Deploy `/backend` to Railway & Connect Inngest Cloud

1. **Create Project on Railway**:
   - Go to [railway.app](https://railway.app) and click **"New Project"** -> **"Deploy from GitHub repo"**.
   - Select your `networkai` repository.
2. **Configure Service Settings**:
   - In **Settings** -> **Root Directory**, set to `/backend` (or leave root as Railway auto-detects `railway.json`).
   - In **Settings** -> **Build**, Railway will use the `Dockerfile` with Astral's `uv`.
3. **Set Environment Variables in Railway**:
   Add the following variables in the Railway dashboard:
   ```env
   SUPABASE_URL=https://your-project.supabase.co/rest/v1/
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   GEMINI_API_KEY=your-gemini-api-key
   INNGEST_EVENT_KEY=your-inngest-event-key
   INNGEST_SIGNING_KEY=your-inngest-signing-key
   PORT=8000
   ENVIRONMENT=production
   ```
4. **Deploy & Copy Public URL**:
   - In **Settings** -> **Networking**, click **"Generate Domain"** (e.g. `https://networkai-backend.up.railway.app`).
   - Test health check: `https://networkai-backend.up.railway.app/health`.
5. **Connect Inngest Cloud**:
   - Go to [app.inngest.com](https://app.inngest.com) -> **Apps** -> **Sync New App**.
   - Enter your public Inngest webhook URL:
     `https://networkai-backend.up.railway.app/api/inngest`
   - Inngest will automatically register the two cron jobs:
     - `scheduled-builder-discovery` (runs every 6 hours: `0 */6 * * *`)
     - `stale-followup-checker` (runs daily at 9:00 AM IST / `30 3 * * *` UTC)

---

### Step 3: Deploy `/frontend` to Vercel

1. **Import Project on Vercel**:
   - Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
   - Select your `networkai` repository.
2. **Configure Project Settings**:
   - Set **Root Directory** to `frontend`.
   - Framework Preset: **Next.js**.
3. **Configure Environment Variables**:
   Add the following under **Environment Variables**:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   NEXT_PUBLIC_API_URL=https://networkai-backend.up.railway.app
   ```
4. **Deploy**:
   - Click **Deploy**. Vercel will build and assign your live domain (e.g. `https://networkai.vercel.app`).

---

### Step 4: Install Mobile PWA & Test LinkedIn Mobile Share Sheet

1. **Install PWA on Android or iOS**:
   - Open your Vercel URL (`https://networkai.vercel.app`) in mobile Chrome (Android) or mobile Safari (iOS).
   - **Android**: Tap **"Install App"** in the bottom action bar (or Chrome menu -> **"Add to Home screen"** / **"Install app"**).
   - **iOS**: Tap the Safari Share button -> **"Add to Home Screen"**.
   - NetworkAI opens full-screen like a native mobile app with standalone display.
2. **Test LinkedIn Mobile Share Target**:
   - Open the official LinkedIn app on your phone.
   - Navigate to any interesting AI builder's profile or post.
   - Tap **Share** -> **Share via...** -> Select **NetworkAI**.
   - The PWA intercepts the shared URL and text via `/share`, sends it to `/api/analyze-profile`, and redirects to your mobile action queue with the generated draft ready for 1-tap review.
3. **1-Tap Approval Flow**:
   - Tap **"Copy & Open LinkedIn"** on any card.
   - The personalized draft is copied to your clipboard, approved in the backend, and the profile opens directly in LinkedIn for instant pasting and sending!

---

### Step 5: Configure Chrome Extension Side Panel

1. Open `chrome://extensions` in Google Chrome on your desktop.
2. Enable **Developer mode** in the top right.
3. Click **"Load unpacked"** and select the `/extension` directory.
4. Click the NetworkAI extension icon in your toolbar to open the native Chrome Side Panel.
5. Tap **⚙️ Settings** in the side panel header:
   - For local development: Keep `http://localhost:8000`.
   - For production: Paste your live Railway URL (`https://networkai-backend.up.railway.app`) and click **Save**.
6. Browse LinkedIn, navigate to any profile or post, and click **✨ Analyze Current Page** to generate and review drafts right beside the page!
