// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import TopNav from './components/TopNav';
import RegisterAccounts from './components/RegisterAccounts';
import UpdateAccount from './components/UpdateAccount';
import DeregisterAccounts from './components/DeregisterAccounts';

const App = () => {
  const API_ENDPOINT = '/api';

  return (
    <Router>
      <div>
        <TopNav />
        <div style={{ padding: 20 }}>
          <Routes>
            <Route path="/register_accounts" element={<RegisterAccounts apiEndpoint={API_ENDPOINT} />} />
            <Route path="/update_account" element={<UpdateAccount apiEndpoint={API_ENDPOINT} />} />
            <Route path="/deregister_accounts" element={<DeregisterAccounts apiEndpoint={API_ENDPOINT} />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
};

export default App;
