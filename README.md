# Wildfire analysis in Türkiye
Due to the frequent wildfires in Turkey, we were developed that analysis project by **Filiz Buzkıran (@lizlavigne) ,  Göknil Bilge (@GoknilBilge) and Ada Erkan (@adaerkn)**.


## Key Features

* ***Machine Learning-Powered Predictions:*** Utilizes a **Random Forest Classifier** trained on historical fire and weather data to predict the likelihood of a forest fire.
* ***Real-Time Weather Integration:*** Fetches live and 5-day forecast weather data from the **OpenWeatherMap API**.
* ***Interactive Web Application:*** Built with **Streamlit**, the app provides a user-friendly interface for selecting a city, viewing risk predictions, and analyzing weather trends.
* ***Geospatial Visualization:*** An interactive **Folium map** displays historical fire locations, offering a geographical context to the risk predictions.


## Project Structure

* `main.py`: This script handles the core machine learning workflow. It loads and preprocesses data, trains the Random Forest model, and saves the trained model to a `.pkl` file for later use.
* `app1.py`: The main application file. It loads the pre-trained model, interacts with the OpenWeatherMap API, calculates the fire risk, and visualizes the results using Streamlit and Folium.
* `yangin_ve_hava_verisi.csv`: A dataset containing historical fire and weather information used to train the machine learning model.
* `orman_yangini_model.pkl`: The serialized machine learning model, created by `main.py` and used by `app1.py` for making predictions.


## How to use

1. Please download the **zip document** and open to use in your IDE tools.
2. `main.py`: This document includes that csv document for the model training.
3. `app1.py`: The file is needed to run our interface. You can immidiatly run the file by typing **"streamlit run app1.py"** in the locale. This command redirects to the website.


## Application Screenshots
Here are some screenshots to give you a better idea of the application's interface:

### ![Current Weather and Risk Prediction](assets/capture_20250830162805075.bmp)

### ![5-Day Risk Forecast](assets/capture_20250830162823763.bmp)

### ![Weather Factors Graph](assets/capture_20250830162831825.bmp)

### ![Wildfire Locations Map](assets/capture_20250830162748054.bmp)

## Data Source

The project uses a custom dataset (`yangin_ve_hava_verisi.csv`) that combines historical fire occurrences with corresponding weather data. This data forms the basis for the machine learning model's training.

