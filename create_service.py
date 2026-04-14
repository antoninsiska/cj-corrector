#!/usr/bin/env python3
"""
Creates the macOS Automator Quick Action (Service) that appears in
right-click → Services → "Correct Czech Grammar".

macOS TCC blocks Automator services from reading files in ~/Documents/.
Fix: copy the two scripts the service needs into ~/.cj_correcter/ (always
accessible) and point the workflow shell script there.
"""
import os
import plistlib
import shutil
import uuid

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR = os.path.expanduser("~/.cj_correcter")        # TCC-safe location
SERVICE_NAME = "Correct Czech Grammar"
SERVICE_DIR  = os.path.expanduser(
    f"~/Library/Services/{SERVICE_NAME}.workflow/Contents"
)

# Scripts the Automator service calls directly
SERVICE_SCRIPTS = ["grammar_correct.py", "ollama_client.py"]


def sync_scripts():
    """Copy runtime scripts to ~/.cj_correcter/ so Automator can reach them."""
    os.makedirs(INSTALL_DIR, exist_ok=True)
    for name in SERVICE_SCRIPTS:
        src = os.path.join(SCRIPT_DIR, name)
        dst = os.path.join(INSTALL_DIR, name)
        shutil.copy2(src, dst)
        print(f"  copied  {name}  →  {dst}")


def build_workflow(python_path: str) -> dict:
    # Run from ~/.cj_correcter/ — not Documents — to avoid TCC denial
    shell_script = (
        "#!/bin/bash\n"
        f'export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:$PATH"\n'
        f'"{python_path}" "{INSTALL_DIR}/grammar_correct.py"\n'
    )
    return {
        "AMApplicationBuild": "521.1",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [
            {
                "action": {
                    "AMAccepts": {
                        "Container": "List",
                        "Optional": True,
                        "Types": ["com.apple.cocoa.string"],
                    },
                    "AMActionVersion": "2.0.3",
                    "AMApplication": ["Automator"],
                    "AMParameterProperties": {
                        "COMMAND_STRING": {},
                        "CheckedForUserDefaultShell": {},
                        "inputMethod": {},
                        "shell": {},
                        "source": {},
                    },
                    "AMProvides": {
                        "Container": "List",
                        "Types": ["com.apple.cocoa.string"],
                    },
                    "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
                    "ActionName": "Run Shell Script",
                    "ActionParameters": {
                        "COMMAND_STRING": shell_script,
                        "CheckedForUserDefaultShell": True,
                        "inputMethod": 0,
                        "shell": "/bin/bash",
                        "source": "",
                    },
                    "BundleIdentifier": "com.apple.RunShellScript",
                    "CFBundleVersion": "2.0.3",
                    "CanShowSelectedItemsWhenRun": False,
                    "CanShowWhenRun": True,
                    "Category": ["AMCategoryUtilities"],
                    "Class Name": "RunShellScriptAction",
                    "InputUUID": str(uuid.uuid4()).upper(),
                    "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
                    "OutputUUID": str(uuid.uuid4()).upper(),
                    "UUID": str(uuid.uuid4()).upper(),
                    "UnlockPassword": "",
                    "arguments": {},
                    "isViewVisible": 1,
                    "location": "309.000000:253.000000",
                    "nibPath": (
                        "/System/Library/Automator/Run Shell Script.action"
                        "/Contents/Resources/English.lproj/main.nib"
                    ),
                },
                "isViewVisible": 1,
            }
        ],
        "connectors": {},
        "workflowMetaData": {
            "workflowType": 2,
            "applicationBundleIDsByPath": {},
            "applicationPaths": [],
            "inputTypeIdentifier": "com.apple.Automator.text",
            "outputTypeIdentifier": "com.apple.Automator.text",
            "presentationMode": 15,
            "processesInput": 1,
            "serviceInputTypeIdentifier": "com.apple.Automator.text",
            "serviceOutputTypeIdentifier": "com.apple.Automator.text",
            "serviceProcessesInput": 1,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def main():
    python_path = shutil.which("python3") or "/usr/bin/python3"
    print(f"Python:  {python_path}")
    print(f"Install: {INSTALL_DIR}")
    print()

    # 1. Copy scripts to TCC-safe location
    print("Copying scripts to ~/.cj_correcter/ (bypasses Automator sandbox)…")
    sync_scripts()
    print()

    # 2. Write Automator workflow
    os.makedirs(SERVICE_DIR, exist_ok=True)

    workflow  = build_workflow(python_path)
    wflow_path = os.path.join(SERVICE_DIR, "document.wflow")
    with open(wflow_path, "wb") as f:
        plistlib.dump(workflow, f, fmt=plistlib.FMT_XML)

    # 3. Info.plist (required for service registration)
    info = {
        "NSServices": [{
            "NSMenuItem":    {"default": SERVICE_NAME},
            "NSMessage":     "doService",
            "NSPortName":    SERVICE_NAME,
            "NSSendTypes":   ["NSStringPboardType"],
            "NSReturnTypes": ["NSStringPboardType"],
        }]
    }
    with open(os.path.join(SERVICE_DIR, "Info.plist"), "wb") as f:
        plistlib.dump(info, f, fmt=plistlib.FMT_XML)

    print(f"✅  Service installed:")
    print(f"   ~/Library/Services/{SERVICE_NAME}.workflow")
    print()
    print("Next steps:")
    print("  1. System Settings → Keyboard → Keyboard Shortcuts → Services")
    print(f"     Enable '{SERVICE_NAME}' under Text.")
    print("  2. Select text → right-click → Services → Correct Czech Grammar")
    print()
    print("Note: if it doesn't appear after enabling, run:")
    print("  /System/Library/CoreServices/pbs -update")


if __name__ == "__main__":
    main()
