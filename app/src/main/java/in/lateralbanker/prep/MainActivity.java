package in.lateralbanker.prep;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.View;
import android.widget.FrameLayout;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.browser.customtabs.CustomTabColorSchemeParams;
import androidx.browser.customtabs.CustomTabsIntent;

public class MainActivity extends Activity {

    private WebView web;
    private FrameLayout root;
    private WebView panel;   // Google answer shown inside the Ask Mentor screen

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#0F1729"));

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // keeps "My Mistakes" and added questions
        s.setSupportMultipleWindows(false);    // target=_blank links come to shouldOverrideUrlLoading

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if ("file".equals(scheme)) return false;          // the app's own page
                // Every outside link (AI apps, bank sites, RBI) opens in the
                // installed app for that link, or the browser if none.
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, uri));
                } catch (ActivityNotFoundException e) {
                    // nothing can open it; ignore
                }
                return true;
            }
        });

        web.addJavascriptInterface(new Bridge(), "Android");
        root = new FrameLayout(this);
        root.addView(web, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);
        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl("file:///android_asset/index.html");
        }
    }

    /** Lets the page open a web page in an in-app panel (Custom Tab) that returns to the app on close. */
    class Bridge {
        @JavascriptInterface
        public void openInApp(final String url) {
            runOnUiThread(() -> openTab(url));
        }

        @JavascriptInterface
        public void showPanel(final String url, final int topCssPx) {
            runOnUiThread(() -> openPanel(url, topCssPx));
        }

        @JavascriptInterface
        public void closePanel() {
            runOnUiThread(() -> hidePanel(false));
        }
    }

    /** Shows a web page inside the app, below the Ask Mentor header (topCssPx = header bottom in CSS pixels). */
    private void openPanel(String url, int topCssPx) {
        Uri uri = Uri.parse(url);
        if (!"https".equals(uri.getScheme())) return;
        hidePanel(false);
        panel = new WebView(this);
        WebSettings ps = panel.getSettings();
        ps.setJavaScriptEnabled(true);
        ps.setDomStorageEnabled(true);
        panel.setBackgroundColor(Color.WHITE);
        panel.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String scheme = request.getUrl().getScheme();
                // Web links (sources) stay inside the panel; app-only links (intent:, market:) are ignored.
                return !("https".equals(scheme) || "http".equals(scheme));
            }
        });
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT);
        lp.topMargin = Math.round(topCssPx * getResources().getDisplayMetrics().density);
        root.addView(panel, lp);
        panel.loadUrl(url);
    }

    private boolean panelOpen() {
        return panel != null;
    }

    private void hidePanel(boolean notifyPage) {
        if (panel == null) return;
        root.removeView(panel);
        panel.destroy();
        panel = null;
        if (notifyPage) web.evaluateJavascript("window.onPanelClosed && window.onPanelClosed()", null);
    }

    private void openTab(String url) {
        Uri uri = Uri.parse(url);
        if (!"https".equals(uri.getScheme())) return;
        try {
            CustomTabColorSchemeParams colors = new CustomTabColorSchemeParams.Builder()
                    .setToolbarColor(Color.parseColor("#0F1729")).build();
            CustomTabsIntent tab = new CustomTabsIntent.Builder()
                    .setDefaultColorSchemeParams(colors).setShowTitle(true).build();
            tab.launchUrl(this, uri);
        } catch (Exception e) {
            try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) { }
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (panelOpen()) {
            if (panel.canGoBack()) panel.goBack();
            else hidePanel(true);
            return;
        }
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
