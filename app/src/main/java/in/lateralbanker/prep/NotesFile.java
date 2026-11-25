package in.lateralbanker.prep;

import android.annotation.TargetApi;
import android.app.Activity;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** The "Detailed Banking Notes 2026" PDF that ships inside the app: a readable copy for the viewer and saving to Downloads. */
final class NotesFile {

    static final String ASSET = "notes/banking-notes-2026.pdf";
    static final String TOC_ASSET = "notes/banking-notes-2026.json";
    static final String FILE_NAME = "Lateral-Banker-Prep-Banking-Notes-2026.pdf";
    static final String FOLDER = "Lateral Banker Prep";
    static final String PREFS = "notes";
    static final int REQ_SAVE = 4107;

    private NotesFile() { }

    /** PdfRenderer needs a real file, so the PDF is copied once from the app into its cache (again after an app update). */
    static File cachedCopy(Context c) throws IOException {
        File f = new File(c.getCacheDir(), "banking-notes-2026.pdf");
        long installed = 0;
        try {
            installed = c.getPackageManager().getPackageInfo(c.getPackageName(), 0).lastUpdateTime;
        } catch (Exception ignored) { }
        if (!f.exists() || f.length() == 0 || f.lastModified() < installed) {
            File tmp = new File(c.getCacheDir(), "banking-notes-2026.tmp");
            try (InputStream in = c.getAssets().open(ASSET); OutputStream out = new FileOutputStream(tmp)) {
                copy(in, out);
            }
            if (f.exists() && !f.delete()) throw new IOException("old copy locked");
            if (!tmp.renameTo(f)) throw new IOException("rename failed");
        }
        return f;
    }

    /** Chapters and sections with their page index (0-based), written when the PDF is built. */
    static JSONArray toc(Context c) {
        try (InputStream in = c.getAssets().open(TOC_ASSET)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            copy(in, out);
            return new JSONObject(out.toString("UTF-8")).getJSONArray("toc");
        } catch (Exception e) {
            return new JSONArray();
        }
    }

    /** Last page read (0-based), or -1 if the notes were never opened. */
    static int lastPage(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt("last", -1);
    }

    static void setLastPage(Context c, int page) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putInt("last", page).apply();
    }

    /**
     * Saves the PDF for the user. Android 10 and newer: straight into Downloads/Lateral Banker Prep (no permission needed).
     * Older phones: the system "Save to" screen, finished in {@link #onSaveResult}.
     */
    static void save(final Activity a) {
        if (Build.VERSION.SDK_INT >= 29) {
            new Thread(() -> {
                String msg;
                try {
                    saveToDownloads(a);
                    msg = "PDF saved in Downloads › " + FOLDER;
                } catch (Exception e) {
                    msg = "Couldn't save the PDF – please try again";
                }
                final String m = msg;
                a.runOnUiThread(() -> Toast.makeText(a, m, Toast.LENGTH_LONG).show());
            }).start();
        } else {
            Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE);
            i.setType("application/pdf");
            i.putExtra(Intent.EXTRA_TITLE, FILE_NAME);
            try {
                a.startActivityForResult(i, REQ_SAVE);
            } catch (Exception e) {
                Toast.makeText(a, "This phone has no screen for saving files", Toast.LENGTH_LONG).show();
            }
        }
    }

    @TargetApi(29)
    private static void saveToDownloads(Context c) throws IOException {
        ContentResolver cr = c.getContentResolver();
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
        String folder = Environment.DIRECTORY_DOWNLOADS + "/" + FOLDER + "/";
        Uri uri = null;
        // Overwrite our own earlier copy instead of creating "name (1).pdf" on every tap.
        try (Cursor cur = cr.query(collection, new String[]{MediaStore.MediaColumns._ID},
                MediaStore.MediaColumns.DISPLAY_NAME + "=? AND " + MediaStore.MediaColumns.RELATIVE_PATH + "=?",
                new String[]{FILE_NAME, folder}, null)) {
            if (cur != null && cur.moveToFirst()) uri = ContentUris.withAppendedId(collection, cur.getLong(0));
        } catch (Exception ignored) { }
        boolean fresh = uri == null;
        if (fresh) {
            ContentValues v = new ContentValues();
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, FILE_NAME);
            v.put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf");
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, folder);
            v.put(MediaStore.MediaColumns.IS_PENDING, 1);
            uri = cr.insert(collection, v);
            if (uri == null) throw new IOException("could not create the file");
        }
        try (InputStream in = c.getAssets().open(ASSET); OutputStream out = cr.openOutputStream(uri, "wt")) {
            if (out == null) throw new IOException("could not open the file");
            copy(in, out);
        }
        if (fresh) {
            ContentValues done = new ContentValues();
            done.put(MediaStore.MediaColumns.IS_PENDING, 0);
            cr.update(uri, done, null, null);
        }
    }

    /** Finishes saving on Android 7–9 after the user picked a place in the "Save to" screen. */
    static void onSaveResult(final Activity a, int resultCode, Intent data) {
        if (resultCode != Activity.RESULT_OK || data == null || data.getData() == null) return;
        final Uri uri = data.getData();
        new Thread(() -> {
            String msg;
            try (InputStream in = a.getAssets().open(ASSET); OutputStream out = a.getContentResolver().openOutputStream(uri, "w")) {
                if (out == null) throw new IOException("could not open the file");
                copy(in, out);
                msg = "PDF saved";
            } catch (Exception e) {
                msg = "Couldn't save the PDF – please try again";
            }
            final String m = msg;
            a.runOnUiThread(() -> Toast.makeText(a, m, Toast.LENGTH_LONG).show());
        }).start();
    }

    private static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        out.flush();
    }
}
