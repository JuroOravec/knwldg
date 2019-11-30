# knwldg/template

## Overview

### Contents

#### Directories

- `data` - Where generated data sits
- `input` - Where input data sits
- `log` - Where logs from running code sits
- `scripts` - Bash (or other non-python) scripts
- `package-name` - Where source code sits

#### Files

Top-level files are package manager or config files, e.g.

- `Pipfile`
- `Pipfile.lock`
- `scrapy.cfg`

## Create new package

To create a new package within the knwldg repo:

1. Copy and rename the `template` folder (and the source code folder too)
2. Display the new folder in the VS Code workspace by adding it `folders` settings in `knwldg/knwldg.code-workspace`

   ```json
   {
     "folders": [
       {
         "path": "my-new-package"
       },
       {
         "path": "common"
       },
       {
         "name": "knwldg",
         "path": "."
       }
     ],
     "settings": {}
   }
   ```

3. Do not display the new folder within the `knwldg` folder by adding it to `files.exclude` settings in `knwldg/.vscode/settings.json`

   ```json
   {
     "files.exclude": {
       "my-new-package": true
     }
   }
   ```

4. Initialize virtual envrionment in the top-level of the new folder.

   ```bash
   pipenv --python 3.7
   ```

5. Run

   ```bash
   pipenv --venv
   ```

   and update the `python.pythonPath` settings in `knwldg/my-new-package/.vscode/settings.json` to point to the venv's python exec.

6. Update the namespaces in `knwldg/my-new-package/scrapy.cfg`

   ```cfg
   # my-new-package/scrapy.cfg

   [settings]
   default = my_new_package.settings

   [deploy]
   project = my_new_package
   ```

7. Configure the Pipfile at `knwldg/my-new-package/Pipfile` if necessary.

8. Update `README.md`

9. Now you should be good to go! Just don't forget to write new spiders and components in `knwldg/my-new-package/my_new_package`
