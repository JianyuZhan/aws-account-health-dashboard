import React from 'react';
import { AppBar, Tabs, Tab, Container } from '@material-ui/core';
import AccountManagement from './components/AccountManagement';
import HealthEvents from './components/HealthEvents';

function App() {
    const [tabValue, setTabValue] = React.useState(0);

    const handleTabChange = (event, newValue) => {
        setTabValue(newValue);
    };

    return (
        <div>
            <AppBar position="static">
                <Tabs value={tabValue} onChange={handleTabChange}>
                    <Tab label="Account Management" />
                    <Tab label="Health Events" />
                </Tabs>
            </AppBar>
            <Container>
                {tabValue === 0 && <AccountManagement />}
                {tabValue === 1 && <HealthEvents />}
            </Container>
        </div>
    );
}

export default App;