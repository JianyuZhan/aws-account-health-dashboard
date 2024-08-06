import React from 'react';
import Pagination from '@mui/material/Pagination';
import Box from '@mui/material/Box';

const PaginationComponent = ({ totalPages, page, handlePageChange }) => (
  <Box mt={2} display="flex" justifyContent="center">
    <Pagination
      count={totalPages}
      page={page}
      onChange={handlePageChange}
    />
  </Box>
);

export default PaginationComponent;
