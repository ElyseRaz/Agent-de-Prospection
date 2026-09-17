import { useState } from "react";
import type { ReactNode } from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import type { SelectChangeEvent } from "@mui/material/Select";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Avatar from "@mui/material/Avatar";
import Menu from "@mui/material/Menu";
import MenuIcon from "@mui/icons-material/Menu";
import RadarIcon from "@mui/icons-material/Radar";
import SearchIcon from "@mui/icons-material/Search";
import ViewKanbanIcon from "@mui/icons-material/ViewKanban";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PersonIcon from "@mui/icons-material/Person";
import LogoutIcon from "@mui/icons-material/Logout";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useCurrentUser, useLogout } from "../../hooks/useAuth";
import { useProfiles } from "../../hooks/useProfiles";
import { useAuthStore } from "../../store/authStore";

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { to: "/", label: "Tableau de bord", icon: <DashboardIcon /> },
  { to: "/jobs", label: "Offres", icon: <SearchIcon /> },
  { to: "/pipeline", label: "Pipeline", icon: <ViewKanbanIcon /> },
  { to: "/profile", label: "Profil", icon: <PersonIcon /> },
];

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useLogout();
  const { data: user } = useCurrentUser();
  const { data: profiles } = useProfiles();
  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const setActiveProfileId = useAuthStore((s) => s.setActiveProfileId);

  const handleProfileChange = (event: SelectChangeEvent<string>) => {
    setActiveProfileId(event.target.value || null);
  };

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Toolbar sx={{ gap: 1 }}>
        <RadarIcon color="primary" />
        <Typography variant="h6" noWrap component="div" fontWeight={700}>
          RemoteRadar
        </Typography>
      </Toolbar>
      <List sx={{ px: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.to}
            component={NavLink}
            to={item.to}
            selected={location.pathname === item.to}
            sx={{ borderRadius: 1, mb: 0.5 }}
            onClick={() => setMobileOpen(false)}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{ width: { md: `calc(100% - ${DRAWER_WIDTH}px)` }, ml: { md: `${DRAWER_WIDTH}px` } }}
      >
        <Toolbar sx={{ gap: 2 }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(true)}
            sx={{ display: { md: "none" } }}
            aria-label="Ouvrir le menu de navigation"
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }} />
          {profiles && profiles.length > 0 && (
            <Select
              size="small"
              value={activeProfileId ?? ""}
              onChange={handleProfileChange}
              displayEmpty
              sx={{ minWidth: 200 }}
              aria-label="Profil actif"
            >
              <MenuItem value="">
                <em>Aucun profil actif</em>
              </MenuItem>
              {profiles.map((profile) => (
                <MenuItem key={profile.id} value={profile.id}>
                  {profile.name}
                </MenuItem>
              ))}
            </Select>
          )}
          <IconButton onClick={(event) => setAnchorEl(event.currentTarget)} aria-label="Menu utilisateur">
            <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main" }}>
              {user?.email?.[0]?.toUpperCase() ?? "U"}
            </Avatar>
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            <MenuItem disabled>{user?.email}</MenuItem>
            <MenuItem
              onClick={() => {
                setAnchorEl(null);
                logout();
                navigate("/login");
              }}
            >
              <ListItemIcon>
                <LogoutIcon fontSize="small" />
              </ListItemIcon>
              Se deconnecter
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{ display: { xs: "none", md: "block" }, "& .MuiDrawer-paper": { width: DRAWER_WIDTH, borderRight: "1px solid #e5e7eb" } }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          p: { xs: 2, md: 3 },
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}
