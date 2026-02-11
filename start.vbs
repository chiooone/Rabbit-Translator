Set shell = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

shell.CurrentDirectory = currentDir
shell.Run "cmd /c start.bat", 0, False
