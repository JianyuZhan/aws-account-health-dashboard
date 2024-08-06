export const registerAccounts = /* GraphQL */ `
  mutation RegisterAccounts($accounts: String!) {
    registerAccounts(accounts: $accounts)
  }
`;

export const updateAccount = /* GraphQL */ `
  mutation UpdateAccount($accountId: String!, $params: String!) {
    updateAccount(accountId: $accountId, params: $params)
  }
`;

export const deregisterAccount = /* GraphQL */ `
  mutation DeregisterAccount($accountId: String!) {
    deregisterAccount(accountId: $accountId)
  }
`;
