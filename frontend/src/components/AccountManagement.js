import React, { useState } from 'react';
import { TextField, Button, Typography } from '@material-ui/core';
import { API, graphqlOperation } from 'aws-amplify';
import { registerAccounts, updateAccount, deregisterAccount } from '../graphql/mutations';

function AccountManagement() {
    const [accountId, setAccountId] = useState('');
    const [crossAccountRole, setCrossAccountRole] = useState('');
    const [allowedUsers, setAllowedUsers] = useState('');

    const handleRegister = async () => {
        const accounts = JSON.stringify({
            [accountId]: {
                cross_account_role: crossAccountRole,
                allowed_users: JSON.parse(allowedUsers),
            },
        });
        const response = await API.graphql(graphqlOperation(registerAccounts, { accounts }));
        console.log(response);
    };

    const handleUpdate = async () => {
        const params = JSON.stringify({
            add: JSON.parse(allowedUsers),
            delete: {},
            update: {},
        });
        const response = await API.graphql(graphqlOperation(updateAccount, { accountId, params }));
        console.log(response);
    };

    const handleDeregister = async () => {
        const response = await API.graphql(graphqlOperation(deregisterAccount, { accountId }));
        console.log(response);
    };

    return (
        <div>
            <Typography variant="h6">Account Management</Typography>
            <TextField label="Account ID" value={accountId} onChange={(e) => setAccountId(e.target.value)} />
            <TextField
                label="Cross Account Role"
                value={crossAccountRole}
                onChange={(e) => setCrossAccountRole(e.target.value)}
            />
            <TextField
                label="Allowed Users (JSON)"
                value={allowedUsers}
                onChange={(e) => setAllowedUsers(e.target.value)}
            />
            <Button onClick={handleRegister}>Register Account</Button>
            <Button onClick={handleUpdate}>Update Account</Button>
            <Button onClick={handleDeregister}>Deregister Account</Button>
        </div>
    );
}

export default AccountManagement;
