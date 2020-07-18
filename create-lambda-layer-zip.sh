FILEPATH=python/lib/python3.8/site-packages
mkdir -p $FILEPATH

read -r -p 'Requirements.txt file location: ' requirementFileLoc
read -r -p 'Name of .zip file: ' zipName

if [ -z "$requirementFileLoc" ]; then
    requirementFileLoc='requirements.txt'
fi

virtualenv tmp_venv
source tmp_venv/bin/activate
pip install -r $requirementFileLoc -t $FILEPATH

zip -r "../${zipName}.zip" $FILEPATH -x "*.git" -x "*.idea" -x "tmp_venv"
rm -rf python
rm -rf tmp_venv
