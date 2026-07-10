; FountainPen Manager Windows Installer Script
; Inno Setup 6.x

#define MyAppName "FountainPen Manager"
#define MyAppVersion "0.2.88"
#define MyAppPublisher "FountainPen Community"
#define MyAppURL "https://github.com/sloogy/FPM/releases"
#define MyAppExeName "FountainPenManager.exe"

[Setup]
SourceDir=..
AppId={{5A7E1C8F-6A0D-4DE2-BF8-CF0000000265}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\FountainPen Manager
DefaultGroupName=FountainPen Manager
AllowNoIcons=yes
DisableProgramGroupPage=no
InfoBeforeFile=README.md
OutputDir=release
OutputBaseFilename=FountainPenManager_Setup_{#MyAppVersion}
SetupIconFile=assets\fountainpen.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
CloseApplications=force
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\FountainPenManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\BENUTZERHANDBUCH_DE.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nutzerdaten bleiben bewusst erhalten.

[Code]
var
  DataDirPage: TInputDirWizardPage;
  PrefsPage: TWizardPage;
  CbLanguage: TNewComboBox;
  CbCurrency: TNewComboBox;
  PreviousDataDir: String;

function JsonEscape(const S: String): String;
begin
  Result := S;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
end;

procedure AddLabel(APage: TWizardPage; const ACaption: String; ATop: Integer);
var
  L: TNewStaticText;
begin
  L := TNewStaticText.Create(APage);
  L.Parent := APage.Surface;
  L.Top := ATop;
  L.Left := 0;
  L.AutoSize := True;
  L.Caption := ACaption;
end;

function InstallerUpdateMode: Boolean;
begin
  Result := ExpandConstant('{param:UPDATE_MODE|0}') = '1';
end;

function ExtractJsonStringValue(const Json, Key: String): String;
var
  Pattern: String;
  StartPos: Integer;
  ValueStart: Integer;
  ValueEnd: Integer;
  Rest: String;
begin
  Result := '';
  Pattern := '"' + Key + '":';
  StartPos := Pos(Pattern, Json);
  if StartPos = 0 then Exit;
  Rest := Copy(Json, StartPos + Length(Pattern), Length(Json));
  ValueStart := Pos('"', Rest);
  if ValueStart = 0 then Exit;
  Delete(Rest, 1, ValueStart);
  ValueEnd := Pos('"', Rest);
  if ValueEnd = 0 then Exit;
  Result := Copy(Rest, 1, ValueEnd - 1);
  StringChangeEx(Result, '\\', '\', True);
  StringChangeEx(Result, '\"', '"', True);
end;

function ExistingDataDirFromMarker: String;
var
  MarkerFile: String;
  AppDir: String;
  JsonText: AnsiString;
begin
  Result := '';
  AppDir := WizardDirValue;
  if AppDir = '' then
    AppDir := ExpandConstant('{autopf}\FountainPen Manager');
  MarkerFile := AddBackslash(AppDir) + 'installation.json';
  if FileExists(MarkerFile) then
  begin
    if LoadStringFromFile(MarkerFile, JsonText) then
      Result := ExtractJsonStringValue(JsonText, 'data_directory');
  end;
end;

function InitialDataDir: String;
var
  ParamDataDir: String;
begin
  ParamDataDir := ExpandConstant('{param:DATA_DIR|}');
  if ParamDataDir <> '' then
    Result := ParamDataDir
  else if PreviousDataDir <> '' then
    Result := PreviousDataDir
  else
    Result := ExpandConstant('{userdocs}\FountainPen Manager');
end;

procedure InitializeWizard;
var
  y: Integer;
begin
  PreviousDataDir := ExistingDataDirFromMarker;

  DataDirPage := CreateInputDirPage(wpSelectDir,
    CustomMessage('DataDirTitle'),
    CustomMessage('DataDirSubtitle'),
    CustomMessage('DataDirDescription') + #13#10#13#10 +
    CustomMessage('DataDirUninstallNote'),
    False, '');
  DataDirPage.Add('');
  DataDirPage.Values[0] := InitialDataDir;

  PrefsPage := CreateCustomPage(DataDirPage.ID,
    CustomMessage('PrefsTitle'),
    CustomMessage('PrefsSubtitle'));

  y := ScaleY(4);
  AddLabel(PrefsPage, CustomMessage('LanguageLabel'), y);
  CbLanguage := TNewComboBox.Create(PrefsPage);
  CbLanguage.Parent := PrefsPage.Surface;
  CbLanguage.Style := csDropDownList;
  CbLanguage.Top := y + ScaleY(16);
  CbLanguage.Left := 0;
  CbLanguage.Width := PrefsPage.SurfaceWidth;
  CbLanguage.Items.Add('Deutsch');
  CbLanguage.Items.Add('English');
  CbLanguage.Items.Add('Français');
  if ActiveLanguage = 'english' then
    CbLanguage.ItemIndex := 1
  else if ActiveLanguage = 'french' then
    CbLanguage.ItemIndex := 2
  else
    CbLanguage.ItemIndex := 0;

  y := y + ScaleY(52);
  AddLabel(PrefsPage, CustomMessage('CurrencyLabel'), y);
  CbCurrency := TNewComboBox.Create(PrefsPage);
  CbCurrency.Parent := PrefsPage.Surface;
  CbCurrency.Style := csDropDownList;
  CbCurrency.Top := y + ScaleY(16);
  CbCurrency.Left := 0;
  CbCurrency.Width := PrefsPage.SurfaceWidth;
  CbCurrency.Items.Add(CustomMessage('CurrencyCHF'));
  CbCurrency.Items.Add(CustomMessage('CurrencyEUR'));
  CbCurrency.Items.Add(CustomMessage('CurrencyUSD'));
  CbCurrency.Items.Add(CustomMessage('CurrencyGBP'));
  CbCurrency.ItemIndex := 0;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if InstallerUpdateMode then
  begin
    if (PageID = DataDirPage.ID) or (PageID = PrefsPage.ID) then
      Result := True;
  end;
end;

function SelectedLanguageCode: String;
begin
  case CbLanguage.ItemIndex of
    1: Result := 'en';
    2: Result := 'fr';
  else
    Result := 'de';
  end;
end;

function SelectedCurrencyCode: String;
begin
  case CbCurrency.ItemIndex of
    1: Result := 'EUR';
    2: Result := 'USD';
    3: Result := 'GBP';
  else
    Result := 'CHF';
  end;
end;

function SelectedRegionCode: String;
begin
  case CbCurrency.ItemIndex of
    1: Result := 'EU';
    2: Result := 'US';
    3: Result := 'GB';
  else
    Result := 'CH';
  end;
end;

function SelectedDecimalSep: String;
begin
  if CbCurrency.ItemIndex = 1 then
    Result := ','
  else
    Result := '.';
end;

function SelectedThousandsSep: String;
begin
  if CbCurrency.ItemIndex = 1 then
    Result := '.'
  else if CbCurrency.ItemIndex = 0 then
    Result := ''''
  else
    Result := ',';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
  ConfigFile: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := DataDirPage.Values[0];
    if DataDir = '' then
      DataDir := InitialDataDir;

    SaveStringToFile(ExpandConstant('{app}\installation.json'),
      '{' + #13#10 +
      '  "install_type": "windows_installer",' + #13#10 +
      '  "version": "{#MyAppVersion}",' + #13#10 +
      '  "app_directory": "' + JsonEscape(ExpandConstant('{app}')) + '",' + #13#10 +
      '  "data_directory": "' + JsonEscape(DataDir) + '"' + #13#10 +
      '}', False);

    ForceDirectories(DataDir);
    ForceDirectories(DataDir + '\backups');
    ForceDirectories(DataDir + '\updates');
    ConfigFile := DataDir + '\config.json';
    if not FileExists(ConfigFile) then
    begin
      Json :=
        '{' + #13#10 +
        '  "initial_settings": {' + #13#10 +
        '    "language": "' + SelectedLanguageCode + '",' + #13#10 +
        '    "default_currency": "' + SelectedCurrencyCode + '",' + #13#10 +
        '    "locale_region": "' + SelectedRegionCode + '",' + #13#10 +
        '    "locale_decimal_sep": "' + JsonEscape(SelectedDecimalSep) + '",' + #13#10 +
        '    "locale_thousands_sep": "' + JsonEscape(SelectedThousandsSep) + '",' + #13#10 +
        '    "locale_currency_position": "before"' + #13#10 +
        '  }' + #13#10 +
        '}';
      SaveStringToFile(ConfigFile, Json, False);
    end;
  end;
end;

[CustomMessages]
german.CreateDesktopIcon=Symbol auf dem Desktop erstellen
german.LaunchProgram=%1 starten
german.UninstallProgram=%1 deinstallieren
german.DataDirTitle=Datenverzeichnis auswählen
german.DataDirSubtitle=Wo sollen Ihre FountainPen-Manager-Daten gespeichert werden?
german.DataDirDescription=Wählen Sie den Ordner, in dem Datenbank, Backups und Update-Cache gespeichert werden sollen.
german.DataDirUninstallNote=Hinweis: Dieses Verzeichnis wird NICHT bei der Deinstallation gelöscht.
german.PrefsTitle=FountainPen-Manager-Einstellungen
german.PrefsSubtitle=Sprache und Währung. Diese Werte werden beim ersten Start übernommen und können später geändert werden.
german.LanguageLabel=Sprache:
german.CurrencyLabel=Währung:
german.CurrencyCHF=CHF – Schweizer Franken
german.CurrencyEUR=EUR – Euro
german.CurrencyUSD=USD – US-Dollar
german.CurrencyGBP=GBP – Britisches Pfund
english.CreateDesktopIcon=Create a desktop icon
english.LaunchProgram=Launch %1
english.UninstallProgram=Uninstall %1
english.DataDirTitle=Select data folder
english.DataDirSubtitle=Where should FountainPen Manager store your data?
english.DataDirDescription=Choose the folder where database, backups and update cache should be stored.
english.DataDirUninstallNote=Note: this folder will NOT be deleted when uninstalling.
english.PrefsTitle=FountainPen Manager settings
english.PrefsSubtitle=Language and currency. These values are used on first start and can be changed later.
english.LanguageLabel=Language:
english.CurrencyLabel=Currency:
english.CurrencyCHF=CHF – Swiss franc
english.CurrencyEUR=EUR – Euro
english.CurrencyUSD=USD – US dollar
english.CurrencyGBP=GBP – British pound
french.CreateDesktopIcon=Créer une icône sur le bureau
french.LaunchProgram=Lancer %1
french.UninstallProgram=Désinstaller %1
french.DataDirTitle=Choisir le dossier de données
french.DataDirSubtitle=Où FountainPen Manager doit-il enregistrer vos données ?
french.DataDirDescription=Choisissez le dossier où seront stockés la base de données, les sauvegardes et le cache de mise à jour.
french.DataDirUninstallNote=Remarque : ce dossier ne sera PAS supprimé lors de la désinstallation.
french.PrefsTitle=Paramètres de FountainPen Manager
french.PrefsSubtitle=Langue et devise. Ces valeurs sont appliquées au premier démarrage et peuvent être modifiées ensuite.
french.LanguageLabel=Langue :
french.CurrencyLabel=Devise :
french.CurrencyCHF=CHF – franc suisse
french.CurrencyEUR=EUR – euro
french.CurrencyUSD=USD – dollar américain
french.CurrencyGBP=GBP – livre sterling
