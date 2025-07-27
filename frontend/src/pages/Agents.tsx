import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  IconButton,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  PlayArrow as StartIcon,
  Stop as StopIcon,
} from '@mui/icons-material';
import { agentApi, Agent, AgentConfig } from '../services/api';

const Agents: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newAgent, setNewAgent] = useState<AgentConfig>({
    name: '',
    description: '',
    type: 'autonomous',
    capabilities: [],
    resources: { memory: '1GB', cpu: '1 core' },
    parameters: {},
  });

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await agentApi.getAgents();
      setAgents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async () => {
    try {
      await agentApi.createAgent(newAgent);
      setCreateDialogOpen(false);
      setNewAgent({
        name: '',
        description: '',
        type: 'autonomous',
        capabilities: [],
        resources: { memory: '1GB', cpu: '1 core' },
        parameters: {},
      });
      await loadAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create agent');
    }
  };

  const handleDeleteAgent = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this agent?')) {
      try {
        await agentApi.deleteAgent(id);
        await loadAgents();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete agent');
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'stopped':
      case 'terminated':
        return 'default';
      case 'error':
        return 'error';
      case 'initializing':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Agents ({agents.length})
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Agent
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {agents.map((agent) => (
          <Grid item xs={12} sm={6} md={4} key={agent.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                  <Typography variant="h6" component="div">
                    {agent.name}
                  </Typography>
                  <Box>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDeleteAgent(agent.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>

                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {agent.description || 'No description'}
                </Typography>

                <Box mb={2}>
                  <Chip
                    label={agent.status}
                    color={getStatusColor(agent.status) as any}
                    size="small"
                  />
                </Box>

                <Typography variant="body2" gutterBottom>
                  <strong>Type:</strong> {agent.type}
                </Typography>

                <Typography variant="body2" gutterBottom>
                  <strong>Capabilities:</strong>
                </Typography>
                <Box mb={1}>
                  {agent.capabilities.map((capability) => (
                    <Chip
                      key={capability}
                      label={capability}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>

                <Typography variant="body2" color="text.secondary">
                  Created: {new Date(agent.created_at).toLocaleDateString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create Agent Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Agent</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Agent Name"
            fullWidth
            variant="outlined"
            value={newAgent.name}
            onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
            sx={{ mb: 2 }}
          />
          
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            value={newAgent.description}
            onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
            sx={{ mb: 2 }}
          />

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Agent Type</InputLabel>
            <Select
              value={newAgent.type}
              label="Agent Type"
              onChange={(e) => setNewAgent({ ...newAgent, type: e.target.value })}
            >
              <MenuItem value="autonomous">Autonomous</MenuItem>
              <MenuItem value="reactive">Reactive</MenuItem>
              <MenuItem value="collaborative">Collaborative</MenuItem>
            </Select>
          </FormControl>

          <TextField
            margin="dense"
            label="Capabilities (comma-separated)"
            fullWidth
            variant="outlined"
            placeholder="code_generation, data_analysis, web_browsing"
            onChange={(e) => {
              const capabilities = e.target.value.split(',').map(cap => cap.trim()).filter(cap => cap);
              setNewAgent({ ...newAgent, capabilities });
            }}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateAgent} variant="contained" disabled={!newAgent.name}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Agents;