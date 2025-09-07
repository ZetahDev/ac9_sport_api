# Favicon and Web App Manifest

This directory contains favicon and Progressive Web App (PWA) assets for AC9 Sport API.

## Files

### Favicon Files
- `favicon.ico` - Traditional favicon in ICO format (16x16, 32x32)
- `icons/icon-16x16.png` - Small favicon for browser tabs
- `icons/icon-32x32.png` - Standard favicon size
- `icons/icon-180x180.png` - Apple touch icon size
- `icons/icon-192x192.png` - Android home screen icon
- `icons/icon-512x512.png` - Large icon for splash screens

### Web App Manifest
- `site.webmanifest` - PWA manifest file defining app metadata and icons

## Endpoints

The following endpoints are available to serve these assets:

- `GET /favicon.ico` - Serves the favicon.ico file
- `GET /site.webmanifest` - Serves the web app manifest
- `GET /manifest.json` - Alternative path for the web app manifest
- `GET /static/icons/*` - Direct access to icon files
- `GET /static/*` - Access to any static assets

All endpoints support both GET and HEAD HTTP methods.

## Usage in HTML

To use these assets in your frontend application, add the following to your HTML `<head>` section:

```html
<!-- Traditional favicon -->
<link rel="icon" href="/favicon.ico" sizes="any">

<!-- Modern PNG favicons -->
<link rel="icon" href="/static/icons/icon-16x16.png" sizes="16x16" type="image/png">
<link rel="icon" href="/static/icons/icon-32x32.png" sizes="32x32" type="image/png">

<!-- Apple touch icon -->
<link rel="apple-touch-icon" href="/static/icons/icon-180x180.png">

<!-- Web App Manifest -->
<link rel="manifest" href="/site.webmanifest">

<!-- Theme color for browser UI -->
<meta name="theme-color" content="#1976d2">
```

## Customization

To customize the branding:

1. Replace the icon files in `static/icons/` with your brand's logos
2. Update `static/favicon.ico` with your brand's favicon
3. Modify `static/site.webmanifest` to reflect your app's name, colors, and metadata

Ensure all icon files maintain the same dimensions as specified in their filenames.

## Testing

Run the favicon tests to verify the implementation:

```bash
python -m pytest tests/test_favicon.py -v
```

This ensures all endpoints work correctly and icon paths in the manifest are accessible.