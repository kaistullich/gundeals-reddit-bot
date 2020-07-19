./zip-codebase.sh
aws lambda update-function-code --function-name gundeals-reddit-new-post-collector --zip-file fileb://../lambda_codebase.zip --publish
aws lambda update-function-code --function-name gundeals-reddit-new-post-notifier --zip-file fileb://../lambda_codebase.zip --publish