import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import TopNav from './components/TopNav';
import RegisterAccounts from './components/account/RegisterAccounts';
import UpdateAccount from './components/account/UpdateAccount';
import DeregisterAccounts from './components/account/DeregisterAccounts';
import AfterRegister from './components/account/AfterRegister'; 
import HealthEventsDashboard from './components/health_event_dashboard/HealthEventsDashboard'; 

const App = () => {
  const API_ENDPOINT = '/api';

  return (
    <Router>
      <div>
        <TopNav />  {/* 导航栏组件 */}
        <div style={{ padding: 20 }}>
          <Routes>
            <Route path="/register_accounts" element={<RegisterAccounts apiEndpoint={API_ENDPOINT} />} />
            <Route path="/update_account" element={<UpdateAccount apiEndpoint={API_ENDPOINT} />} />
            <Route path="/deregister_accounts" element={<DeregisterAccounts apiEndpoint={API_ENDPOINT} />} />
            <Route path="/after_register" element={<AfterRegister />} />
            <Route path="/health_events" element={<HealthEventsDashboard apiEndpoint={API_ENDPOINT} />} />  {/* 传递 apiEndpoint 属性 */}
          </Routes>
        </div>
      </div>
    </Router>
  );
};

export default App;