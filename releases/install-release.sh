
RELEASE_LOCATION="./wiki-dags"
VALUES_FILE="values.yaml"
CHART_VARIABLES_FILE="chart-variables.yaml"

VALUES_FILEPATH="$RELEASE_LOCATION/$VALUES_FILE"
CHART_VARIABLES_FILEPATH="$RELEASE_LOCATION/$CHART_VARIABLES_FILE"

# # Read each variable from the YAML file and add it to the associative array
# declare -A chart_variables
# while IFS= read -r line; do
#   name=$(echo "$line" | yq e '.name' -)
#   variables[$name]=""
# done < <(yq e '.variables[]' $YAML_FILE)

# Chart Variables
REPOSITORY=$(yq e '.repository' $CHART_VARIABLES_FILEPATH)
TAG=$(yq e '.tag' $CHART_VARIABLES_FILEPATH)
NAMESPACE=$(yq e '.namespace' $CHART_VARIABLES_FILEPATH)
RELEASE_NAME=$(yq e '.releaseName' $CHART_VARIABLES_FILEPATH)
CHART_NAME=$(yq e '.chartName' $CHART_VARIABLES_FILEPATH)

CHART_FULLNAME="$REPOSITORY/$CHART_NAME"
VALUES_FILEPATH="$RELEASE_LOCATION/$VALUES_FILE"

echo "Installing $CHART_FULLNAME..."

helm upgrade --install $RELEASE_NAME $CHART_FULLNAME --version $TAG --namespace $NAMESPACE -f $VALUES_FILEPATH
