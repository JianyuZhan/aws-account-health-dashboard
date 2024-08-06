import React, { useState } from 'react';
import { TextField, Button, Typography, Container, Box, Grid, IconButton, Card, CardContent, CardActions, Snackbar, Alert } from '@mui/material';
import { Add as AddIcon, Remove as RemoveIcon } from '@mui/icons-material';
import config from '../../config';

const DeregisterAccounts = () => {
  const [accountIds, setAccountIds] = useState(['']);
  const [errors, setErrors] = useState({});
  const [alert, setAlert] = useState({ open: false, severity: 'info', message: '', autoHideDuration: 6000 });

  const handleAccountIdChange = (index, event) => {
    const newAccountIds = [...accountIds];
    newAccountIds[index] = event.target.value;
    setAccountIds(newAccountIds);
  };

  const handleAddAccountId = () => {
    setAccountIds([...accountIds, '']);
  };

  const handleRemoveAccountId = (index) => {
    const newAccountIds = accountIds.filter((_, i) => i !== index);
    setAccountIds(newAccountIds);
  };

  const validateFields = () => {
    const newErrors = {};
    accountIds.forEach((accountId, index) => {
      if (!accountId) {
        newErrors[`accountId-${index}`] = '帐号 ID 是必填项';
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleDeregister = () => {
    if (!validateFields()) {
      console.log('Validation failed');
      return;
    }

    setAlert({ open: true, severity: 'info', message: '删除中...', autoHideDuration: null });

    const body = {
      account_ids: accountIds
    };

    console.log('Sending request to API:', config.API_ENDPOINT);
    console.log('Request body:', JSON.stringify(body));

    fetch(`${config.API_ENDPOINT}/deregister_accounts`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    .then(response => {
      console.log('Response status:', response.status);
      console.log('Response status text:', response.statusText);
      if (!response.ok) {
        return response.text().then(text => {
          setAlert({ open: true, severity: 'error', message: `Error ${response.status}: ${text}`, autoHideDuration: 6000 });
          throw new Error(text);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Response from API:', data);
      setAlert({ open: true, severity: 'success', message: '删除成功', autoHideDuration: 6000 });
    })
    .catch(error => {
      console.error('Error:', error);
      setAlert({ open: true, severity: 'error', message: `删除失败: ${error.message}`, autoHideDuration: 6000 });
    });
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          批量删除组织帐号
        </Typography>
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              帐号 ID 列表
            </Typography>
            {accountIds.map((accountId, index) => (
              <Grid container spacing={2} alignItems="center" key={index}>
                <Grid item xs={11}>
                  <TextField
                    label={`帐号 ID ${index + 1}`}
                    variant="outlined"
                    fullWidth
                    value={accountId}
                    onChange={(e) => handleAccountIdChange(index, e)}
                    error={!!errors[`accountId-${index}`]}
                    helperText={errors[`accountId-${index}`]}
                  />
                </Grid>
                <Grid item xs={1}>
                  {index === 0 ? (
                    <IconButton color="primary" onClick={handleAddAccountId}>
                      <AddIcon />
                    </IconButton>
                  ) : (
                    <IconButton color="secondary" onClick={() => handleRemoveAccountId(index)}>
                      <RemoveIcon />
                    </IconButton>
                  )}
                </Grid>
              </Grid>
            ))}
          </CardContent>
        </Card>
        <CardActions>
          <Grid container spacing={2} justifyContent="flex-end">
            <Grid item>
              <Button variant="contained" color="primary" onClick={handleDeregister}>
                删除帐号
              </Button>
            </Grid>
          </Grid>
        </CardActions>
      </Box>
      <Snackbar 
        open={alert.open} 
        onClose={handleCloseAlert} 
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }} 
        autoHideDuration={alert.autoHideDuration}
      >
        <Alert onClose={handleCloseAlert} severity={alert.severity} sx={{ width: '100%' }}>
          {alert.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default DeregisterAccounts;
