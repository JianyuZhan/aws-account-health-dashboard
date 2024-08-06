import React, { useState } from 'react';
import { TextField, Button, Typography, Container, Box, Grid, IconButton, Card, CardContent, CardActions } from '@mui/material';
import { Add as AddIcon, Remove as RemoveIcon } from '@mui/icons-material';
import config from '../config';

const DeregisterAccounts = () => {
  const [accountIds, setAccountIds] = useState(['']);
  const [errors, setErrors] = useState({});

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
        return response.text().then(text => { throw new Error(text) });
      }
      return response.json();
    })
    .then(data => {
      console.log('Response from API:', data);
      alert('删除成功');
    })
    .catch(error => {
      console.error('Error:', error);
      alert('删除失败，请检查控制台日志获取更多信息');
    });
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
    </Container>
  );
};

export default DeregisterAccounts;
