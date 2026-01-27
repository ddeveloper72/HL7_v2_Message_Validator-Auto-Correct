# Environment Configuration Setup

## .env File Configuration

The application uses a `.env` file to store sensitive configuration like API keys.

### Setup Instructions

1. **Open the `.env` file** in the project root directory
2. **Paste your Gazelle API key** after `GAZELLE_API_KEY=`

Example:
```
GAZELLE_API_KEY=your-actual-api-key-here
VERIFY_SSL=True
```

### Getting an API Key

Contact Gazelle support to obtain your API key:
- IHE Gazelle: https://gazelle.ihe.net
- eHealth Ireland support

### Security Notes

⚠️ **IMPORTANT:**
- The `.env` file is already listed in `.gitignore` - it will NOT be committed to git
- Never share your API key or commit it to version control
- Keep your `.env` file secure and private

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `GAZELLE_API_KEY` | Your Gazelle EVS API key | (empty) |
| `VERIFY_SSL` | Enable SSL certificate verification | `True` |

### Verifying Configuration

When you start the Flask app, you should see:
```
Starting Flask application...
EVS API Endpoint: https://testing.ehealthireland.ie/evs/rest/validations
SSL Verification: True
API Key Configured: Yes ✓
```

If you see "API Key Configured: No", check that:
1. The `.env` file exists
2. You've added your API key after `GAZELLE_API_KEY=`
3. There are no extra spaces or quotes around the key

### Testing

Once configured, test the API with:
```powershell
# Open browser to http://127.0.0.1:5000
# Click "Validate Sample File" button
# Or upload your own HL7 v2 XML file
```

The API key will automatically be included in all requests to Gazelle EVS.
