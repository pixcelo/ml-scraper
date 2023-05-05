import pickle
import lightgbm as lgb

# Load the model from the pickle file
with open('model/model.pkl', 'rb') as file:
    model = pickle.load(file)

# Get the feature column names
feature_names = model.feature_name()

# Get the total number of columns
num_columns = len(feature_names)

# Print the feature column names and the total number of columns
print("Feature names:", feature_names)
print("Total number of columns:", num_columns)
