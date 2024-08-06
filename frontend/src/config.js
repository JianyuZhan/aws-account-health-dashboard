const apiEndpoint = process.env.REACT_APP_API_ENDPOINT;
if (!apiEndpoint) {
  throw new Error("Missing API_ENDPOINT environment variable");
}

const config = {
  API_ENDPOINT: apiEndpoint
};

module.exports = config;