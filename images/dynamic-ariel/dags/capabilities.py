class AzureBlob:
    def __init__(self, blob_path, data="TEST DATA"):
        self.blob_path = blob_path 
        self.data = data 
    def get_value(self):
        return self.data
    def set_value(self, data):
        self.data = data
    def get_path(self):
        return self.blob_path

def ArielAFR(document:AzureBlob, output_document:AzureBlob, model_id:str):
    val = document.get_value()
    transformed_val = val + f"\nTransformed using AFR with model_id: {model_id}."
    output_document.set_value(transformed_val)

def ArielASI(document:AzureBlob, output_document:AzureBlob, recipe_id:str):
    val = document.get_value()
    transformed_val = val + f"\nTransformed using ASI with recipe_id: {recipe_id}."
    output_document.set_value(transformed_val)
