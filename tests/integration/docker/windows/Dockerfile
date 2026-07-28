# escape=`
# Windows Server Core validates the native Windows code path, unit tests, and
# PyInstaller packaging. It cannot validate Desktop/App Installer/WinGet GUI
# installs; those require a disposable Windows 10/11 VM.
FROM python:3.12-windowsservercore-ltsc2022

SHELL ["powershell.exe", "-NoLogo", "-ExecutionPolicy", "Bypass", "-Command"]

WORKDIR C:\workstation-setup
COPY . .

RUN python -m pip install --no-cache-dir -e '.[dev]'

CMD ["powershell.exe", "-NoLogo"]
