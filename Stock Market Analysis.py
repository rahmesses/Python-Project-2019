# -*- coding: utf-8 -*-
"""
Created on Sat Dec  7 16:02:33 2019

@author: Rahmesses
"""

import pandas as pd
import numpy as np
import re
import nltk
import keras
from nltk.sentiment.vader import SentimentIntensityAnalyzer as SIA
nltk.download('all')
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize,sent_tokenize
from nltk.tag import pos_tag
from nltk.stem.porter import *
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import LinearSVC
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout
from keras.optimizers import SGD, adam
import xgboost as xgb
from xgboost import XGBClassifier

# Data Merging

print("Data read and joining commences")

news = pd.read_csv('E:/Fall 2019/Python/Project/stocknews/RedditNews.csv')
stocks = pd.read_csv('E:/Fall 2019/Python/Project/stocknews/upload_DJIA_table.csv')

news.head()
stocks.head()

poslist=[]
newslist = []
TopNewslabels = []

for q in range(26):
    TopNewslabels.append('Top'+str(q))

TopNewslabels[0] = 'Date'
TopNewslabels = TopNewslabels + ['Adj Close']

newstop25 = pd.DataFrame(columns = TopNewslabels)

for i in range(len(news['Date'])):
    try:
        newslist.append(news.at[i,'News'])
        if news['Date'][i] != news['Date'][i+1]:
            poslist.append(i)
    except KeyError:
        break

k=0
e=0
l=[]
while e < len(poslist):
    l.append(newslist[k:poslist[e]+1])
    k = poslist[e]+1
    e+=1 
        
p = 0    
while p < len(poslist):
    newstop25.set_value(p,'Date',news['Date'][poslist[p]],takeable = False)
    i=0        
    while i < 25:
        try:
            newstop25.at[p,TopNewslabels[i+1]] = l[p][i]
        except IndexError:
            break
        i+=1
    p+=1


combinedNewsStock = newstop25.merge(stocks,on='Date')

combinedNewsStock = combinedNewsStock.drop(['Adj Close_x','Volume'],axis=1)
combinedNewsStock = combinedNewsStock.rename(columns={"Adj Close_y":"Adj Close"})



combinedNewsStock.insert(31,'Net_Change',0) # Open-Close
combinedNewsStock.insert(32,'Net_High',0) #High-Open
combinedNewsStock.insert(33,'Net_Low',0) #Open-Low
combinedNewsStock.insert(34,'Label',0) #1 for stock increase, 0 for stock decrease


for i in range(len(combinedNewsStock)):
    combinedNewsStock.at[i,'Net_Change'] = float(combinedNewsStock.at[i,'Open'] - combinedNewsStock.at[i,'Close'])
    combinedNewsStock.at[i,'Net_High'] = float(combinedNewsStock.at[i,'High'] - combinedNewsStock.at[i,'Open'])
    combinedNewsStock.at[i,'Net_Low'] = float(combinedNewsStock.at[i,'Open'] - combinedNewsStock.at[i,'Low'])
    try:
        if combinedNewsStock.at[i+1,'Adj Close'] > combinedNewsStock.at[i,'Adj Close']:
            combinedNewsStock.at[i+1,'Label'] = 1
        else:
            combinedNewsStock.at[i+1,'Label'] = 0
    except KeyError:
        break
combinedNewsStock.dtypes

print("Data Joining Completed!!")
################################################################################################################################
# Data Cleaning

print("Commence Data Cleaning")
   
combinedNewsStock = combinedNewsStock.fillna('')

for i in range(len(combinedNewsStock)):
    for j in range(25):
        if  combinedNewsStock.iloc[i,j+1] != '' and combinedNewsStock.iloc[i,j+1][0] == 'b':
            combinedNewsStock.iloc[i,j+1]= combinedNewsStock.iloc[i,j+1][1:]

combinedNewsStock.head()

combinedNewsStock.dtypes

################################################################################################################################

# Sentiment Analysis

print("Commence Sentiment Analysis of News Headlines")

sia = SIA()
new_head = pd.DataFrame()

for i in range(len(combinedNewsStock)):
    for j in range(25):
        try:
            pol_score = sia.polarity_scores(combinedNewsStock.iloc[i,j+1])
            df = pd.DataFrame.from_records([pol_score])
            #df['label'] = 0
            df.loc[df['compound'] >= 0, 'label'] = 1
            df.loc[df['compound'] < 0, 'label'] = 0
            new_head.loc[i,j]= df['label'][0].astype(int)
        except AttributeError:
            continue

new_head.columns = TopNewslabels[1:26]        

#for z in range(len(combinedNewsStock)):
new_head['Net_Change'] = combinedNewsStock['Net_Change']
new_head['Net_High'] = combinedNewsStock['Net_High']
new_head['New_Low'] = combinedNewsStock['Net_Low']
new_head['Label'] = combinedNewsStock['Label']

new_head.dtypes
#creating a list of positive, negative headlines
pos= []
neg = []
for i in range(len(new_head)):
    for j in range(25):
        if new_head.iloc[i,j] == 1:
            pos.append(combinedNewsStock.iloc[i,j+1])
        elif new_head.iloc[i,j] == 0:
            neg.append(combinedNewsStock.iloc[i,j+1])
            
#print("Positive: ", len(pos))
#print("Negative: ", len(neg))

swlist = stopwords.words('english')
stemmer = PorterStemmer()

pos_corpus = []
neg_corpus= []
for f in pos:
    
    # match any special character and remove it (other than _)
    processed_content = re.sub(r'\W+', ' ', f.lower()) 
    
    # text into tokens
    words = word_tokenize(processed_content)
    
    # Attaching part of speech to each word
    pos_words = pos_tag(words) #returns a list
    
    clean_words = []
    for w in pos_words:
        if w[0] in swlist or len(w[0]) <=3 or w[1] not in ('JJ','JJR', 'JJS','NN', 'NNS', 'ADJ', 'ADV','VBN', 'VBG'):
            continue
        clean_words.append(stemmer.stem(w[0]))
    
    pos_content = ' '.join(clean_words)
    pos_corpus.append(pos_content)

for f in neg:
    processed_content = re.sub(r'\W+', ' ', f.lower())
    words = word_tokenize(processed_content)
    neg_words = pos_tag(words)
    
    clean_words = []
    for w in neg_words:
        if w[0] in swlist or len(w[0]) <=3 or w[1] not in ('JJ','JJR','JJS', 'NN', 'NNS', 'ADJ', 'ADV','VBN', 'VBG'):
            continue
        clean_words.append(stemmer.stem(w[0]))
    
    neg_content = ' '.join(clean_words)
    neg_corpus.append(neg_content)

#print(len(pos_corpus))
#print(len(neg_corpus))

print("Model Building for a Set of 25 New headlines for a Day")

vectorizer = TfidfVectorizer(ngram_range=(1,1)) #wordcount  #bigram produced lower prediction accuracy
print(vectorizer)
corpus = pos_corpus + neg_corpus

x = vectorizer.fit_transform(corpus)
y = np.array([1]*len(pos_corpus) + [0]*len(neg_corpus))

lr_model_news = LogisticRegression(random_state=1) 

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=1)


lr_model_news.fit(x_train, y_train)
lr_pred_news = lr_model_news.predict(x_test)
lr_acc_news = accuracy_score(y_test, lr_pred_news)
print('Logistic Regression Accuracy: ', lr_acc_news)

scores = cross_val_score(lr_model_news, x, y, cv=10) #using 10 fold crosss validation , which will give you 10 scores
print('10 run scores', scores, ',', np.mean(scores), ',', np.std(scores))

print("Model for Fresh News is Complete. Using this Model to Predict the Sentiment of the Headlines")

##########################################################################################################################################

## Model for Stock Variation prediciton

print("Building Model for Stock Prediction")

X = new_head.loc[:, new_head.columns != 'Label']
Y = new_head.loc[:, new_head.columns == 'Label']

X.shape
Y.shape

X = X.values
Y = Y.values

X.shape
Y.shape

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=10)

# Logistic Regression

Y_train_LR = Y_train.reshape(len(Y_train),)
Y_test_LR = Y_test.reshape(len(Y_test),)

lr_model_stock = LogisticRegression(random_state=1)

lr_model_stock.fit(X_train, Y_train_LR)

lr_pred_stock = lr_model_stock.predict(X_test)
lr_acc_stock = accuracy_score(Y_test_LR, lr_pred_stock)
print('Logistic Regression Accuracy: ', lr_acc_stock)

## XGBoost

modelxg = XGBClassifier()

modelxg.fit(X_train,Y_train)

print(modelxg)

xg_pred = modelxg.predict(X_test)

predictionsxg = [round(value) for value in xg_pred]

accuracy_xg = accuracy_score(Y_test, predictionsxg)
print("XG Boost Accuracy: %.2f%%" % (accuracy_xg * 100.0))

## Deep Learning

model_deep = Sequential()
model_deep.add(Dense(50, input_dim = 28, activation= 'relu'))
#model_deep.add(Dropout(0.2))
model_deep.add(Dense(40, activation= 'relu'))
#model_deep.add(Dropout(0.2))
model_deep.add(Dense(30, activation= 'relu'))
#model_deep.add(Dropout(0.2))
model_deep.add(Dense(20, activation= 'relu'))
#model_deep.add(Dropout(0.2))
model_deep.add(Dense(10, activation= 'relu'))
#model_deep.add(Dropout(0.2))
model_deep.add(Dense(1, activation= 'sigmoid'))

model_deep.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

model_deep.fit(X_train, Y_train, epochs=50, batch_size=10)
test_loss, test_acc = model_deep.evaluate(X_test, Y_test)

print("Deep Learning Accuracy:",test_acc)

## Random Forest
#model_rf = RandomForestRegressor(n_estimators = 1000, random_state = 42)
#model_rf.fit(X_train, Y_train)
#predictionsrf = model_rf.predict(X_test)
# Calculate the absolute errors
#errorsrf = abs(predictionsrf - Y_test)
# Print out the mean absolute error (mae)
#print('Mean Absolute Error:', round(np.mean(errorsrf), 2), 'degrees.')
# Calculate mean absolute percentage error (MAPE)
#mape = 100 * (errorsrf / Y_test)
# Calculate and display accuracy
#accuracyrf = 100 - np.mean(mape)
#print('Accuracy:', round(accuracyrf, 2), '%.')

# Decsion Tree

tree = DecisionTreeClassifier(random_state=42)

tree.fit(X_train_np, Y_train_np)

print(f'Model Accuracy: {tree.score(X_test_np,Y_test_np)}')

# SVM

svc_model = LinearSVC(random_state=1)
pred_SVM = svc_model.fit(X_train, Y_train).predict(X_test)
print("SVC Accuracy:", accuracy_score(Y_test,pred_SVM, normalize = True))

print("The End")

################################################################################################






