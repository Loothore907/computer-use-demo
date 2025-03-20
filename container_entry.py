#!/usr/bin/env python3
import os
import sys
import subprocess

# Force bypass of Streamlit welcome screen
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = "false"
os.environ['STREAMLIT_SERVER_HEADLESS'] = "true"

# Create all necessary Streamlit configuration files
streamlit_config_path = os.path.expanduser("~/.streamlit")
os.makedirs(streamlit_config_path, exist_ok=True)

# credentials.toml - bypasses email prompt
credentials_file = os.path.join(streamlit_config_path, "credentials.toml")
with open(credentials_file, "w") as f:
    f.write("""
[general]
email = ""
showWelcomeOnStartup = false
    """)

# config.toml - disables telemetry and header
config_file = os.path.join(streamlit_config_path, "config.toml")
with open(config_file, "w") as f:
    f.write("""
[browser]
gatherUsageStats = false
serverAddress = "0.0.0.0"

[server]
headless = true
runOnSave = false
enableCORS = true
enableXsrfProtection = false
fileWatcherType = "none"
    """)

# Create first-run marker
with open(os.path.join(streamlit_config_path, ".first_run_complete"), "w") as f:
    f.write("1")

# Print configuration files for debugging
print(f"Created {credentials_file}:")
with open(credentials_file, "r") as f:
    print(f.read())

print(f"Created {config_file}:")
with open(config_file, "r") as f:
    print(f.read())

# Run Streamlit
print("Starting Streamlit...")
subprocess.run(["streamlit", "run", "app.py"]) 