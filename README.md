
# Auction Application
### By: Sophie Newlin
### Date: 3/21/23
In this functionality of this project, users can create login, sign up, create auction item pages, become sellers, write reviews, submit bids, and much more. 
## App.py
App.py contains the functions and SQL required to create the web application.
### Home
The home function is the first screen the user sees when logging on. The functionality in the code in quite simple when compared to the other functions. It simply checks the session to see if a user is logged in and returns the home screen if true or false
### Signup 
The sign up page allows a user to sign up for an account. It takes the email and password input and hashes the password, before storing it into the users table. If a user already has the email input, an error message pops up, otherwise, the user is redirected to the home page. 
### Login 
The login page allows a user to login with their email and password. If there is no email or password with the input credentials, the user is given an error message. If login is successful, the user is redirected to home. 
### Profile 
This page allows the user to change their password. They must input their old password, the new password, and the confirmed new password. If the old password is incorrect or the new password doesn't match the confirmed password, the user gets an error message. If there are no errors, the user's password is changed. 
### Logout
This page allows the user to logout. This means that when the user tries to go to the profile page, they will be prompted to sign in. 
## HTML Pages 
All of the html pages contain a toggle bar at the top of the screen, linking the user to different pages (Home, sign up, login, logout, my profile). It also contains the lionAuction header (temporary). 
### Home.html 
This html is for the home page of lionAuction. It contains the toggle bar and header above, but also contains a sign up button on the header. There is also temporary "Featured Items" cards which will eventually allow users to bid on these items. The current photos are not correct, just placeholders. 
### Signup.html 
This html is for the user to sign up for the lionauction. For this progess review, it only contains the functionality to take a user's email and password. Once created, the user is redirected to the home page. If the user already exists, they get an error message. At the bottom, there is an option to log in if the user already has an account. 
### Login.html
This html file is for the user to sign in to their account. The user is redirected to home after logging in. If the user inputs a wrong password or email, they are prompted to either sign in or retry their password. 
### Profile.html
This html is for the user to change their password. There are three forms: "Old password", "new password", and "confirm password". If the user wants to change their password, they must fill out the three forms. If the old password is wrong or the new password and confirmed password dont match, the user is given an error message. Otherwise, the user's password is changed. 
## Final Thoughts
As stated above, there are already blocks of code anticipating the rest of the project requirements for users, such as their name, address, credit information, phone number, gender, major, etc. Based on my current functionality and design, I do not feel it will be very hard to fix the user table to fit those requirements. 

