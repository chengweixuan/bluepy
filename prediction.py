import os
import numpy as np

import pandas as pd
from tensorflow import keras

from scipy.signal import butter, lfilter

class PredictionManager:
    def __init__(self, data):
        window_size = 64
        sampling_freq = 20
        data = self.scaling(data)
        window_list = np.array(self.segmentation(data, window_size, sampling_freq))
        window_list = window_list.reshape(window_list.shape[0], window_list.shape[1], window_list.shape[2], 1)
        self.data = data
        self.window_list = window_list
        self.model = keras.models.load_model('./BestModel/data_5.1_mlp_fold(0)') # update model path here
    
    def predict(self, X_train):
        Activities_index_name = {0: 'sidepump', 1: 'hair', 2: 'gun'}
        X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], X_train.shape[2], 1)
        pred = self.model.predict(X_train)
        
        max_pred = pred.argmax(axis=1)[0]
        highest_action = Activities_index_name[max_pred]
        
        highest_prob = pred.tolist()[0][max_pred]
        return [highest_action, highest_prob,
                f"\n______________HIGHEST CLASS: {highest_action} ({highest_prob})______________"]
                
    @staticmethod
    def apply_filter(signal, fs=20, cutoff=8, window=21, std=50, order=5):
    
        def butter_low_pass_filter(data, cutoff, fs, order=5):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = butter(order, normal_cutoff, btype='low', analog=False)
            y = lfilter(b, a, data)
            return y
        
        return butter_low_pass_filter(signal, cutoff, fs, order)
    
    @staticmethod
    def apply_rolling(data, modes, columns, window=15):
        rolling_obj = data.rolling(window=window, center=True, min_periods=1)
        rolling_obj_pow = data.pow(2).rolling(window=window, center=True, min_periods=1)
        data_dict = {
            "mean" : rolling_obj.mean(),
            "rms"  : rolling_obj_pow.apply(lambda x: np.sqrt(x.mean())),
            "var"  : rolling_obj.var(),
            "iqr25": rolling_obj.quantile(0.25),
            "iqr75": rolling_obj.quantile(0.75)
        }
        return [pd.DataFrame(data_dict[key], columns=columns).add_prefix(key+"_") for key in modes]
    
    def preprocess(self, window, fs):
        target_columns = ['AccX', 'AccY', 'AccZ', 'GyroYaw', 'GyroPitch', 'GyroRoll']
        
        # low_pass_mean, low_pass_rms, low_pass_iqr25, low_pass_iqr75, jerk, jerk_rms, jerk_std
        df = pd.DataFrame(self.apply_filter(window.copy(), fs=fs), columns=target_columns)
        jerk = df.diff().div(1/fs).fillna(0).add_prefix("jerk_")
        
        df_details = pd.concat(self.apply_rolling(df, ["mean", "rms", "iqr25", "iqr75"], list(df.columns)), axis=1)
        jerk_details = pd.concat(self.apply_rolling(jerk, ["rms", "var"], list(jerk.columns)), axis=1)
        
        return np.array(pd.concat([jerk, df_details, jerk_details], axis=1))
    
    def scaling(self, data):
        u = [-1084.4501307966707, 4618.177693222355, -4742.835743162901, 21.803757431629013, -68.8114149821641, 17.521450653983354] # update here with mean_
        s = [1738.005726213283, 2797.0250897568862, 1875.531057562884, 59.990624437194064, 42.35141488715953, 60.52917362501123] # update here with scale_

        for i in range(0, len(data)):
            for j in range(0, len(data[i])):
                data[i][j] = (data[i][j] - u[j]) / s[j]

        return pd.DataFrame(np.array(data), columns=['AccX', 'AccY', 'AccZ', 'GyroYaw', 'GyroPitch', 'GyroRoll'])
    
    def segmentation(self, data, window_size, fs):
        window_list = []
        for x in range(0, len(data) - window_size - 1):
            window = data.iloc[x:x + window_size]
            window_list.append(self.preprocess(window, fs))
        return window_list
    
    def run(self):
        window_list = self.window_list
        
        result = []
        for window in window_list:
            window = window.reshape(1, window.shape[0], window.shape[1], window.shape[2])
            result.append(self.predict(window))
            
        return result
