# Stock-Market-AI-GUI
Stock Market Prediction &amp; Trading Bot using AI with a Web Interface

## Stock Market Prediction using an LSTM Network
Long Short Term Memory networks – usually just called “LSTMs” – are a special kind of RNN, capable of learning long-term dependencies. They were introduced by Hochreiter & Schmidhuber (1997), and were refined and popularized by many people in following work. They work tremendously well on a large variety of problems, and are now widely used. LSTMs are explicitly designed to avoid the vanishing gradient problem. 

<p align="center">
<img src="./assets/lstm_model.png" align="middle" />  </p>

All recurrent neural networks have the form of a chain of repeating modules of neural network. In standard RNNs, this repeating module will have a very simple structure, such as a single tanh layer. LSTMs also have this chain like structure, but the repeating module has a different structure. Instead of having a single neural network layer, there are four, interacting in a very special way.

For more info check out this [article](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)

## Stock Market Agent using Evolution Strategy Agent

Even though the name sounds fancy but under the hood, it’s perhaps the simplest algorithm you can devise for exploring a landscape. Consider an agent in an environment (like Pong) that’s implemented via a neural network. It takes pixels in the input layer and outputs probabilities of actions available to it (move the paddle up, down or do nothing).

<p align="center">
<img src="./assets/evolve_agent.png" align="middle" />  </p>

Our task in reinforcement learning is to find the parameters (weights and biases) of the neural network (weights and biases) that make the agent win more often and hence get more rewards. 

For more info check out this [article](https://towardsdatascience.com/reinforcement-learning-without-gradients-evolving-agents-using-genetic-algorithms-8685817d84f)

## Requirements
* Python 3.6.2 (https://www.python.org/downloads/release/python-362/)
* Django (https://www.djangoproject.com/)
* Numpy (https://pypi.org/project/numpy/)
* Tensorflow (https://pypi.org/project/tensorflow/)
* Keras (https://pypi.org/project/Keras/)
* Seaborn (https://pypi.org/project/seaborn/)
* Yahoo-Finance (https://pypi.org/project/yahoo-finance/)
* Pandas (https://pypi.org/project/pandas/)
* Matplotlib (https://pypi.org/project/matplotlib/)

## Usage

First start the django server using the following line,
```
python manage.py runserver
```
### Main Page
<p align="center">
<img src="./assets/Main.PNG" align="middle" />  </p>

The main page gives you three options to choose from:

### 1. Stock Info
<p align="center">
<img src="./assets/Info.PNG" align="middle" />  </p>
Just Input the Symbol of the Stock and the Duration for which to get the data and the data is fetched using the yahoo-finance library and graphed using matplotlib and mpld3.
<p align="center">
<img src="./assets/Info-done.png" align="middle" />  </p>
The details are shown in the table and the closing prices are graphed. Hover your mouse over the points will give you a tooltip with the date and the closing price for that day.

### 2. Prediction
<p align="center">
<img src="./assets/Prediction.png" align="middle" />  </p>
For the prediction you have to input the Symbol for the Stock, the Period of Data to train with, The Number of Simulations to run, and the Number of Future Days to predict for.
<p align="center">
<img src="./assets/Prediction-done.png" align="middle" />  </p>
The closing prices of the simulations that are deemed acceptable is graphed using matplotlib and mpld3. Hover your mouse over the points will give you a tooltip with the date and the closing price for that day.

### 3.Trading Agent
<p align="center">
<img src="./assets/Agent.png" align="middle" />  </p>
For the trading agent you have to input the Symbol for the Stock, the Period of Data to trade on, The Initial Fund, and the Number of Days to Skip in between selling or buying.
<p align="center">
<img src="./assets/Agent-done.png" align="middle" />  </p>
The closing prices is graphed and the selling and buying days are marked with their respective markers using matplotlib and mpld3. Hover your mouse over the marker to get the date and the action done on that day.


### 4. Docker usage:
```
docker build -t smag:latest . 
./runOnceDocker.sh 
python manage runserver
```

# G00D LUCK

For doubts email me at:
atinsaki@gmail.com

## Email/mobile OTP accounts

Visitors are redirected to login before accessing the app. Registration collects
a full name, username, phone number, optional email address, date of birth, and
password. A six-digit OTP is sent to the phone by SMS; registration finishes
after that code is verified, then returns to the login page instead of signing
the new user in automatically. The optional email address is not verified and
is not used for account recovery.
Login uses the chosen username and password. Age is calculated from the stored
date of birth.

Configure Twilio for registration SMS delivery:

```text
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_PHONE=your-twilio-number
```

Keep these credentials private and set them in the server environment. OTPs
expire after five minutes, have a five-attempt limit, and are rate-limited.
Apply the authentication database migration with `python manage.py migrate`.
Live registration requires valid Twilio credentials; the app does not print
codes to the server console.

### Forgot password

On the login page choose **Forgot your password?**, enter the account email,
and submit the email OTP together with a strong new password and its
confirmation. On success, the app returns to login and displays a password
changed confirmation. Password reset codes expire after five minutes and are
rate-limited like registration codes.
