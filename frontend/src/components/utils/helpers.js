export const truncateString = (str, num) => {
    if (str.length <= num) {
      return str;
    }
    return str.slice(0, num) + '...';
  };
  
  export const formatValue = (value) => {
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value);
    }
    return value;
  };
  