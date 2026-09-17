import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import Typography from "@mui/material/Typography";

interface EmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 1.5,
        py: 6,
        textAlign: "center",
        color: "text.secondary",
      }}
    >
      <InboxOutlinedIcon fontSize="large" color="disabled" />
      <Typography variant="subtitle1" color="text.primary">
        {title}
      </Typography>
      {description && <Typography variant="body2">{description}</Typography>}
      {actionLabel && onAction && (
        <Button variant="outlined" size="small" onClick={onAction} sx={{ mt: 1 }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}
