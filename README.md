# Lateral Banker Prep – Android app

This folder is a complete Android project. Build it once to get `app-debug.apk`, which you can install on any Android phone (Android 7.0 or newer).

## Option 1 – No software needed (GitHub, free)

1. On github.com, create a new **public** repository named exactly `lateral-banker-prep` (account `cockroachbankersparty01-gif`). It must be public so the app can download the live jobs file.
2. Upload everything in this folder, including the hidden `.github` folder, keeping the folder structure. (Or ask Claude to push it for you once the empty repository exists.)
3. Open the **Actions** tab. The "Build APK" job starts by itself (or click **Run workflow**).
4. After about 3–5 minutes, open the finished run and download **LateralBankerPrep-apk**. Unzip it to get `app-debug.apk`.

## Option 2 – Android Studio

1. Install Android Studio (free) and choose **File › Open** on this folder.
2. Let it finish syncing, then choose **Build › Build App Bundle(s) / APK(s) › Build APK(s)**.
3. Click **locate** in the pop-up to find `app-debug.apk`.

## Installing on a phone

Send the APK to the phone (WhatsApp, Drive or USB), tap it, and allow "Install unknown apps" for that app when asked.

## What works in the app

- Practice tests, mock tests with timer, My Mistakes, Add Question (saved on the phone)
- Exam Calendar and Policy Gist
- Current job openings and results: downloaded from `data/jobs.json` in the GitHub repository every time the app opens (with a Refresh button), and saved on the phone for offline use. Claude's scheduled task updates that file every 3 days, so the app stays current without a new APK.
- Ask Mentor: sends the question to ChatGPT, Claude or Perplexity (opens with the question filled in) or Gemini or Copilot (question copied; paste it in). If the app is installed it opens directly; otherwise its website opens.

The built-in "Ask here" chat runs on Claude, so it is not inside the APK.

## Updating the content

Replace `app/src/main/assets/index.html` with a newer version of the page and build again. Raise `versionCode` and `versionName` in `app/build.gradle` each time.

## Publishing on Google Play

The debug APK is for sharing and testing. For the Play Store you need a signed release build (Android Studio: **Build › Generate Signed App Bundle**) and a Google Play developer account. Use `playstore-icon-512.png` as the store icon. Keep your signing key safe; you need the same key for every update.
