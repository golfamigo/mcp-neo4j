# Neo4j Knowledge Graph Memory MCP Server

## Overview

A Model Context Protocol (MCP) server implementation that provides persistent memory capabilities through Neo4j graph database integration. 

By storing information in a graph structure, this server maintains complex relationships between entities as memory nodes and enables long-term retention of knowledge that can be queried and analyzed across multiple conversations or sessions.

With [Neo4j Aura](https://console.neo4j.io) you can host your own database server for free or share it with your collaborators. Otherwise you can run your own Neo4j server locally.

The MCP server leverages Neo4j's graph database capabilities to create an interconnected knowledge base that serves as an external memory system. Through Cypher queries, it allows exploration and retrieval of stored information, relationship analysis between different data points, and generation of insights from the accumulated knowledge. This memory can be further enhanced with Claude's capabilities.

### Graph Schema

* `Memory` - A node representing an entity with a name, type, and observations.
* `Relationship` - A relationship between two entities with a type.

### Usage Example

```
Let's add some memories 
I, Michael, living in Dresden, Germany work at Neo4j which is headquartered in Sweden with my colleagues Andreas (Cambridge, UK) and Oskar (Gothenburg, Sweden)
I work in Product Management, Oskar in Engineering and Andreas in Developer Relations.
```

Results in Claude calling the create_entities and create_relations tools.

![](./docs/images/employee_create_entities_and_relations.png)

![](./docs/images/employee_graph.png)

## Components

<!--
### Resources
### Prompts
-->
### Tools

The server offers these core tools:

#### Query Tools
- `read_graph`
   - Read the entire knowledge graph
   - No input required
   - Returns: Complete graph with entities and relations

- `search_nodes`
   - Search for nodes based on a query
   - Input:
     - `query` (string): Search query matching names, types, observations
   - Returns: Matching subgraph

- `find_nodes`
   - Find specific nodes by name
   - Input:
     - `names` (array of strings): Entity names to retrieve
   - Returns: Subgraph with specified nodes

#### Entity Management Tools
- `create_entities`
   - Create multiple new entities in the knowledge graph
   - Input:
     - `entities`: Array of objects with:
       - `name` (string): Name of the entity
       - `type` (string): Type of the entity  
       - `observations` (array of strings): Initial observations about the entity
   - Returns: Created entities

- `delete_entities` 
   - Delete multiple entities and their associated relations
   - Input:
     - `entityNames` (array of strings): Names of entities to delete
   - Returns: Success confirmation

#### Relation Management Tools
- `create_relations`
   - Create multiple new relations between entities
   - Input:
     - `relations`: Array of objects with:
       - `source` (string): Name of source entity
       - `target` (string): Name of target entity
       - `relationType` (string): Type of relation
   - Returns: Created relations

- `delete_relations`
   - Delete multiple relations from the graph
   - Input:
     - `relations`: Array of objects with same schema as create_relations
   - Returns: Success confirmation

#### Observation Management Tools
- `add_observations`
   - Add new observations to existing entities
   - Input:
     - `observations`: Array of objects with:
       - `entityName` (string): Entity to add to
       - `contents` (array of strings): Observations to add
   - Returns: Added observation details

- `delete_observations`
   - Delete specific observations from entities
   - Input:
     - `deletions`: Array of objects with:
       - `entityName` (string): Entity to delete from
       - `observations` (array of strings): Observations to remove
   - Returns: Success confirmation

## Usage with Claude Desktop

### Released Package

Can be found on PyPi https://pypi.org/project/mcp-neo4j-memory/

Add the server to your `claude_desktop_config.json` with configuration of 

* db-url (for [Neo4j Aura](https://console.neo4j.io) `neo4j+s://xxxx.databases.neo4j.io` for local `bolt://localhost`)
* username
* password

```json
"mcpServers": {
  "neo4j": {
    "command": "uvx",
    "args": [
      "mcp-neo4j-memory",
      "--db-url",
      "neo4j+s://xxxx.databases.neo4j.io",
      "--username",
      "<your-username>",
      "--password",
      "<your-password>"
    ]
  }
}
```

### Development

```json
# Add the server to your claude_desktop_config.json
"mcpServers": {
  "neo4j": {
    "command": "uv",
    "args": [
      "--directory",
      "parent_of_servers_repo/mcp-neo4j/servers/mcp-neo4j-memory/src/mcp_neo4j_memory",
      "run",
      "mcp-neo4j-memory",
      "--db-url",
      "bolt://localhost",
      "--username",
      "neo4j",
      "--password",
      "<your-password>"
    ]
  }
}
```

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
