from hr_system.hr import create_app, db  # import from hr inside hr_system
import webbrowser

app = create_app()

if __name__ == "__main__":
    print("Running on http://192.168.1.118:5000")
     # Force Flask to open in Chrome
    chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe %s"
    app.run(host="0.0.0.0", port=5000, debug=True)