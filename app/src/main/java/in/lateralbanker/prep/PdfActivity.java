package in.lateralbanker.prep;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.TextUtils;
import android.text.style.StyleSpan;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.util.HashMap;
import java.util.Map;

/**
 * In-app reader for the notes PDF. Android's own PdfRenderer draws each page; the pages are shown in a
 * WebView so the reader gets smooth scrolling and pinch-to-zoom. Remembers the last page read.
 */
public class PdfActivity extends Activity {

    private static final String PAGE_HOST = "pdf.local";

    private final Object lock = new Object();
    private PdfRenderer renderer;
    private ParcelFileDescriptor fd;
    private int pageCount;
    private float[] pageW, pageH;
    private JSONArray toc;
    private int screenW;

    private WebView web;
    private TextView pageLabel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#0F1729"));
        screenW = getResources().getDisplayMetrics().widthPixels;

        try {
            File f = NotesFile.cachedCopy(this);
            fd = ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY);
            renderer = new PdfRenderer(fd);
            pageCount = renderer.getPageCount();
            pageW = new float[pageCount];
            pageH = new float[pageCount];
            for (int i = 0; i < pageCount; i++) {
                PdfRenderer.Page p = renderer.openPage(i);
                pageW[i] = p.getWidth();
                pageH[i] = p.getHeight();
                p.close();
            }
        } catch (Exception e) {
            Toast.makeText(this, "Couldn't open the notes", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        toc = NotesFile.toc(this);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#E9EDF4"));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(Color.parseColor("#0F1729"));
        bar.setPadding(dp(2), 0, dp(6), 0);

        TextView back = barButton("←", 22);
        back.setContentDescription("Back");
        back.setOnClickListener(v -> finish());
        bar.addView(back);

        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        TextView title = new TextView(this);
        title.setText("Banking Notes 2026");
        title.setTextColor(Color.WHITE);
        title.setTextSize(15);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setSingleLine(true);
        title.setEllipsize(TextUtils.TruncateAt.END);
        pageLabel = new TextView(this);
        pageLabel.setTextColor(Color.parseColor("#C9D2E6"));
        pageLabel.setTextSize(12);
        pageLabel.setText("Page 1 of " + pageCount);
        titles.addView(title);
        titles.addView(pageLabel);
        bar.addView(titles, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));

        TextView contents = barButton("Contents", 14);
        contents.setOnClickListener(v -> showContents());
        bar.addView(contents);

        TextView save = barButton("Download", 14);
        save.setTextColor(Color.parseColor("#F29F1A"));
        save.setOnClickListener(v -> NotesFile.save(this));
        bar.addView(save);

        root.addView(bar, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#E9EDF4"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setSupportZoom(true);
        s.setBuiltInZoomControls(true);   // pinch to zoom
        s.setDisplayZoomControls(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        web.addJavascriptInterface(new ViewerBridge(), "Pdf");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                if (PAGE_HOST.equals(u.getHost())) return pageImage(u);
                return null;
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return true;   // the reader never navigates away
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(root);
        web.loadUrl("file:///android_asset/pdfview.html");
    }

    /** Draws one page as a JPEG at the width the page asks for (https://pdf.local/page/N?w=PX). Runs on a WebView worker thread. */
    private WebResourceResponse pageImage(Uri u) {
        try {
            int i = Integer.parseInt(u.getLastPathSegment());
            int w = screenW * 3 / 2;
            String ws = u.getQueryParameter("w");
            if (ws != null) w = Integer.parseInt(ws);
            w = Math.max(240, Math.min(w, 2200));
            byte[] jpg;
            synchronized (lock) {   // PdfRenderer allows one open page at a time
                if (renderer == null || i < 0 || i >= pageCount) return null;
                int h = Math.round(w * pageH[i] / pageW[i]);
                Bitmap bm = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
                bm.eraseColor(Color.WHITE);
                PdfRenderer.Page p = renderer.openPage(i);
                p.render(bm, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                p.close();
                ByteArrayOutputStream out = new ByteArrayOutputStream(256 * 1024);
                bm.compress(Bitmap.CompressFormat.JPEG, 90, out);
                bm.recycle();
                jpg = out.toByteArray();
            }
            WebResourceResponse r = new WebResourceResponse("image/jpeg", null, new ByteArrayInputStream(jpg));
            Map<String, String> headers = new HashMap<>();
            headers.put("Cache-Control", "max-age=86400");
            headers.put("Access-Control-Allow-Origin", "*");
            r.setResponseHeaders(headers);
            return r;
        } catch (Throwable t) {   // includes running out of memory on very old phones: the page asks again, smaller
            return null;
        }
    }

    private void showContents() {
        final int n = toc.length();
        if (n == 0) return;
        CharSequence[] items = new CharSequence[n];
        final int[] pages = new int[n];
        for (int k = 0; k < n; k++) {
            JSONObject t = toc.optJSONObject(k);
            if (t == null) { items[k] = ""; continue; }
            pages[k] = t.optInt("p", 0);
            boolean chapter = t.optInt("l", 1) == 1;
            String text = (chapter ? "" : "      ") + t.optString("t") + "  ·  p. " + (pages[k] + 1);
            SpannableString sp = new SpannableString(text);
            if (chapter) sp.setSpan(new StyleSpan(Typeface.BOLD), 0, text.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            items[k] = sp;
        }
        new AlertDialog.Builder(this)
                .setTitle("Contents")
                .setItems(items, (d, which) -> web.evaluateJavascript("goTo(" + pages[which] + ")", null))
                .setNegativeButton("Close", null)
                .show();
    }

    /** Called by pdfview.html. */
    class ViewerBridge {
        @JavascriptInterface
        public String info() {
            try {
                JSONObject o = new JSONObject();
                o.put("pages", pageCount);
                JSONArray sizes = new JSONArray();
                for (int i = 0; i < pageCount; i++) sizes.put(new JSONArray().put((double) pageW[i]).put((double) pageH[i]));
                o.put("sizes", sizes);
                o.put("last", Math.max(0, NotesFile.lastPage(PdfActivity.this)));
                return o.toString();
            } catch (Exception e) {
                return "{\"pages\":0,\"sizes\":[],\"last\":0}";
            }
        }

        @JavascriptInterface
        public void onPage(final int page) {
            NotesFile.setLastPage(PdfActivity.this, page);
            runOnUiThread(() -> pageLabel.setText("Page " + (page + 1) + " of " + pageCount));
        }
    }

    private TextView barButton(String text, int sp) {
        TextView b = new TextView(this);
        b.setText(text);
        b.setTextColor(Color.WHITE);
        b.setTextSize(sp);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(10), 0, dp(10), 0);
        b.setMinWidth(dp(44));
        b.setMinHeight(dp(48));
        b.setClickable(true);
        b.setFocusable(true);
        return b;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == NotesFile.REQ_SAVE) NotesFile.onSaveResult(this, resultCode, data);
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.stopLoading();
            web.destroy();
        }
        synchronized (lock) {
            try {
                if (renderer != null) renderer.close();
                if (fd != null) fd.close();
            } catch (Exception ignored) { }
            renderer = null;
        }
        super.onDestroy();
    }
}
