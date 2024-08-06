import React, { useState } from 'react';
import { TextField, Button, Typography, Container, Box, Grid, IconButton, Card, CardContent, CardActions, Snackbar, Alert } from '@mui/material';
import { Add as AddIcon, Remove as RemoveIcon } from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import config from '../../config';

const RegisterAccounts = () => {
  const [items, setItems] = useState([{ accountId: '', crossAccountRole: '', allowedUsers: [{ email: '', name: '' }] }]);
  const [errors, setErrors] = useState({});
  const [alert, setAlert] = useState({ open: false, severity: 'info', message: '', autoHideDuration: 6000 });
  const navigate = useNavigate();

  const handleAddItem = () => {
    setItems([...items, { accountId: '', crossAccountRole: '', allowedUsers: [{ email: '', name: '' }] }]);
  };

  const handleRemoveItem = (index) => {
    const newItems = items.filter((_, i) => i !== index);
    setItems(newItems);
  };

  const handleInputChange = (index, event) => {
    const { name, value } = event.target;
    const newItems = [...items];
    newItems[index][name] = value;
    setItems(newItems);
  };

  const handleUserChange = (itemIndex, userIndex, event) => {
    const { name, value } = event.target;
    const newItems = [...items];
    newItems[itemIndex].allowedUsers[userIndex][name] = value;
    setItems(newItems);
  };

  const handleAddUser = (itemIndex) => {
    const newItems = [...items];
    newItems[itemIndex].allowedUsers.push({ email: '', name: '' });
    setItems(newItems);
  };

  const handleRemoveUser = (itemIndex, userIndex) => {
    const newItems = [...items];
    newItems[itemIndex].allowedUsers = newItems[itemIndex].allowedUsers.filter((_, i) => i !== userIndex);
    setItems(newItems);
  };

  const validateFields = () => {
    const newErrors = {};
    items.forEach((item, index) => {
      if (!item.accountId) {
        newErrors[`accountId-${index}`] = '帐号 ID 是必填项';
      }
      if (!item.crossAccountRole) {
        newErrors[`crossAccountRole-${index}`] = '跨账户角色 是必填项';
      }
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleRegister = () => {
    if (!validateFields()) {
      console.log('Validation failed');
      return;
    }

    setAlert({ open: true, severity: 'info', message: '注册中...', autoHideDuration: null });

    const accounts = items.reduce((acc, item) => {
      const allowedUsers = item.allowedUsers.reduce((users, user) => {
        if (user.email && user.name) {
          users[user.email] = user.name;
        }
        return users;
      }, {});
      acc[item.accountId] = {
        cross_account_role: item.crossAccountRole,
        allowed_users: allowedUsers,
      };
      return acc;
    }, {});

    console.log('Sending request to API:', config.API_ENDPOINT);
    console.log('Request body:', JSON.stringify(accounts));

    fetch(`${config.API_ENDPOINT}/register_accounts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(accounts),
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
      setAlert({ open: true, severity: 'success', message: '注册成功', autoHideDuration: 6000 });
      setTimeout(() => {
        navigate('/after_register', { state: { registeredData: accounts } });  // 跳转到 AfterRegister 页面
      }, 1000);
    })
    .catch(error => {
      console.error('Error:', error);
      setAlert({ open: true, severity: 'error', message: `注册失败: ${error.message}`, autoHideDuration: 6000 });
    });
  };

  const handleCloseAlert = () => {
    setAlert({ ...alert, open: false });
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          注册组织帐号
        </Typography>
        {items.map((item, index) => (
          <Card key={index} sx={{ mb: 2 }}>
            <CardContent>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={1}>
                  {index === 0 ? (
                    <IconButton color="primary" onClick={handleAddItem}>
                      <AddIcon />
                    </IconButton>
                  ) : (
                    <IconButton color="secondary" onClick={() => handleRemoveItem(index)}>
                      <RemoveIcon />
                    </IconButton>
                  )}
                </Grid>
                <Grid item xs={3}>
                  <TextField
                    label="帐号 ID"
                    name="accountId"
                    variant="outlined"
                    fullWidth
                    value={item.accountId}
                    onChange={(e) => handleInputChange(index, e)}
                    error={!!errors[`accountId-${index}`]}
                    helperText={errors[`accountId-${index}`]}
                  />
                </Grid>
                <Grid item xs={3}>
                  <TextField
                    label="跨账户角色"
                    name="crossAccountRole"
                    variant="outlined"
                    fullWidth
                    value={item.crossAccountRole}
                    onChange={(e) => handleInputChange(index, e)}
                    error={!!errors[`crossAccountRole-${index}`]}
                    helperText={errors[`crossAccountRole-${index}`]}
                  />
                </Grid>
                <Grid item xs={5}>
                  <Box sx={{ border: '1px solid #ccc', borderRadius: 1, p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      允许的用户
                    </Typography>
                    {item.allowedUsers.map((user, userIndex) => (
                      <Grid container spacing={1} alignItems="center" key={userIndex} sx={{ mb: 1 }}>
                        <Grid item xs={5}>
                          <TextField
                            label="用户邮箱"
                            name="email"
                            variant="outlined"
                            fullWidth
                            value={user.email}
                            onChange={(e) => handleUserChange(index, userIndex, e)}
                          />
                        </Grid>
                        <Grid item xs={5}>
                          <TextField
                            label="用户名"
                            name="name"
                            variant="outlined"
                            fullWidth
                            value={user.name}
                            onChange={(e) => handleUserChange(index, userIndex, e)}
                          />
                        </Grid>
                        <Grid item xs={1}>
                          <IconButton color="primary" onClick={() => handleAddUser(index)}>
                            <AddIcon />
                          </IconButton>
                        </Grid>
                        <Grid item xs={1}>
                          <IconButton color="secondary" onClick={() => handleRemoveUser(index, userIndex)}>
                            <RemoveIcon />
                          </IconButton>
                        </Grid>
                      </Grid>
                    ))}
                    {item.allowedUsers.length === 0 && (
                      <Button
                        variant="outlined"
                        startIcon={<AddIcon />}
                        onClick={() => handleAddUser(index)}
                      >
                        添加用户
                      </Button>
                    )}
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        ))}
        <CardActions>
          <Grid container spacing={2} justifyContent="flex-end">
            <Grid item>
              <Button variant="contained" color="primary" onClick={handleRegister}>
                注册帐号
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

export default RegisterAccounts;