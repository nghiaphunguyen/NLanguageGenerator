
from __future__ import print_function
import httplib2
import os
import re

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
APPLICATION_NAME = 'Language Generator'
CONFIG_FILE_NAME = 'lang-config'

SPREAD_SHEET_ID_KEY = 'SPREAD_SHEET_ID'
SHEET_NAME_KEY = 'SHEET_NAME'
CLIENT_SECRET_FILE_KEY = 'CLIENT_SECRET_FILE'
ENUM_NAME_KEY = 'ENUM_NAME'
ENUM_PATH_KEY = 'ENUM_PATH'
LANGUAGES_PATH_KEY = 'LANGUAGES_PATH'
USE_BASE_LANGUAGE_AS_KEY_KEY = 'USE_BASE_LANGUAGE_AS_KEY'

CONFIGS = {SPREAD_SHEET_ID_KEY: "", SHEET_NAME_KEY: "Sheet1",
 CLIENT_SECRET_FILE_KEY: "client_secret.json",
  ENUM_NAME_KEY: "Text", ENUM_PATH_KEY: "", LANGUAGES_PATH_KEY: "", USE_BASE_LANGUAGE_AS_KEY_KEY: "true"}

LANGUAGES_CODE = {"english" : "en", "vietnamese": "vi", "burmese" : "my"}

REPLACES = {"[STRING]": "%@",
 "[DECIMAL]": "%@",
  "<![CDATA[": "",
   "]]>": "",
    "<u>": "",
     "</u>": "",
      "<b>": "",
      "</b>": "",
      "\\\'": "\'"}

def get_configs():
    print("--------GETTING CONFIGS--------")
    with open(CONFIG_FILE_NAME) as f:
        content = f.readlines()
        for c in content:
            c = c.strip()
            result = re.search(r'(?<=\").*(?=\")', c)
            if not result:
                continue
            for key in CONFIGS:
                if c.startswith(key):
                    CONFIGS[key] = result.group(0)
                    break

    for key in CONFIGS:
        print("{}={}".format(key, CONFIGS[key]))

def ensure_dir(path):
    path = os.path.dirname(path)

    if not os.path.exists(path):
        os.makedirs(path)

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CONFIGS[CLIENT_SECRET_FILE_KEY] , SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    get_configs()
    convertToStringsFromValues(getValuesFromGoogleSheet())
    print("-------------DONE----------")

def getValuesFromGoogleSheet():
    print("--------GETTING VALUES FROM GOOGLE SHEET--------")
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

    spreadsheetId = CONFIGS[SPREAD_SHEET_ID_KEY]
    rangeName = CONFIGS[SHEET_NAME_KEY]
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()

    values = result.get('values', [])
    return values

def formatValue(value):
    value = convertToUTF8(value)
    for replace in REPLACES:
        value = value.replace(replace, REPLACES[replace])
    return value

def formatKey(key):
    components = convertToUTF8(key).split("_")
    result = components[0]
    if len(components) > 1:
        components = components[1:]
        for value in components:
            result += value.title()
    return result

def createTextFile(keys):
    print("------CREATING TEXT FILE---------")
    filename = CONFIGS[ENUM_NAME_KEY]
    path = CONFIGS[ENUM_PATH_KEY]

    result = "import UIKit\n\nenum %s: String {" % filename
    result += "\n"

    for key in keys:
        if CONFIGS[USE_BASE_LANGUAGE_AS_KEY_KEY] == "true":
            result += "\tcase %s = \"%s\"\n" % (key[0], key[1])
        else:
            result += "\tcase %s\n" % key[0]
    result += "\n\tvar text: String {\n"
    result += "\t\treturn NSLocalizedString(\"\\(self.rawValue)\", comment: \"\")\n"
    result += "\t}\n}"

    filePath = os.path.join(path, filename + ".swift")
    writeToFile(filePath, result)

def writeToFile(filePath, string):
    ensure_dir(filePath)
    f = open(filePath, 'w')
    f.write(string)
    f.close()

def createLanguageFiles(keys, languages):
    print("------CREATING LANGUAGE FILES-------")
    subfix = ".lproj"
    filename = "Localizable.strings"
    for i in xrange(len(keys)):
        languageCode = keys[i].lower()
        if languageCode in LANGUAGES_CODE.keys():
            languageCode = LANGUAGES_CODE[languageCode]
        path = os.path.join(CONFIGS[LANGUAGES_PATH_KEY], languageCode + subfix)
        filePath = os.path.join(path, filename)
        writeToFile(filePath, languages[i])

def convertToStringsFromValues(values):
    print("--------CONVERTING TO STRINGS--------")
    if not values or len(values) < 2:
        print('No data found.')
    else:
        keys = values[0][1:]

        enumKeys = list()
        languages = list(xrange(len(keys)))
        for i in xrange(len(languages)):
            languages[i] = ""

        values = values[1:]
        for row in values:
            if len(row) < 2:
                continue

            key = formatKey(row[0])
            baseLanguage = formatValue(row[1])
            if key != "" and baseLanguage != "":
                enumKeys.append((key, baseLanguage))

            row = row[1:]
            if CONFIGS[USE_BASE_LANGUAGE_AS_KEY_KEY] == "true":
                key = baseLanguage

            for i in xrange(len(row)):
                if not row[i] == "":
                    languages[i] += "\"{}\" = \"{}\";\n".format(key, formatValue(row[i]))

        createTextFile(enumKeys)
        createLanguageFiles(keys, languages)
def convertToUTF8(s):
    return s.encode('utf-8')

if __name__ == '__main__':
    main()
