[Setup]
AppName=AI运营分身
AppVersion=1.0
DefaultDirName={autopf}\AI运营分身
DefaultGroupName=AI运营分身
OutputBaseFilename=AI运营分身_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\run.bat

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: ".git\*;.python-core\*;.python-runtime\*;__pycache__\*;*.pyc;*.tmp;*.log;backups\*;dist\*;build\*;.env;local_demo.db;reports\*;activity_plans\*;chroma_db\*;chroma_db_backup*\*;tmp_validation_outputs\*;chart_font_test.png"

[Icons]
Name: "{group}\AI运营分身"; Filename: "{app}\run.bat"; WorkingDir: "{app}"
Name: "{commondesktop}\AI运营分身"; Filename: "{app}\run.bat"; WorkingDir: "{app}"

[Run]
Filename: "{app}\run.bat"; WorkingDir: "{app}"; Description: "启动 AI运营分身（需要本机已安装 Python 3.10+）"; Flags: postinstall skipifsilent nowait

[UninstallDelete]
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
function InitializeSetup(): Boolean;
begin
  MsgBox('此安装包是源代码分发包，需要本机已安装 Python 3.10 或更高版本。运行数据会写入用户数据目录，不会写入安装目录。', mbInformation, MB_OK);
  Result := True;
end;
