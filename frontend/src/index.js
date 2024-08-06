import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import Amplify from 'aws-amplify';
import awsExports from './aws-exports';
Amplify.configure(awsExports);

ReactDOM.render(<App />, document.getElementById('root'));
