export const fetchHealthEvents = /* GraphQL */ `
  query FetchHealthEvents($filters: String!) {
    fetchHealthEvents(filters: $filters) {
      eventId
      eventType
      description
    }
  }
`;
