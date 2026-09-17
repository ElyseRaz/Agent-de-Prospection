import { useMemo, useRef } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddTaskIcon from "@mui/icons-material/AddTask";
import { useNavigate } from "react-router-dom";
import type { Job, ScoreBreakdownItem } from "../../api/types";
import RiskBadge from "./RiskBadge";
import MatchScoreChip from "./MatchScoreChip";

export interface JobTableRow {
  job: Job;
  score?: number;
  breakdown?: ScoreBreakdownItem[];
}

interface JobTableProps {
  rows: JobTableRow[];
  onAddToPipeline?: (job: Job) => void;
  height?: number;
}

const ROW_HEIGHT = 60;

function formatRate(job: Job): string {
  if (!job.rate_min && !job.rate_max) return "—";
  const currency = job.rate_currency ?? "";
  if (job.rate_min && job.rate_max && job.rate_min !== job.rate_max) {
    return `${job.rate_min}-${job.rate_max} ${currency}${job.rate_period ? `/${job.rate_period}` : ""}`;
  }
  const value = job.rate_min ?? job.rate_max;
  return `${value} ${currency}${job.rate_period ? `/${job.rate_period}` : ""}`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("fr-FR");
}

const columnHelper = createColumnHelper<JobTableRow>();

export default function JobTable({ rows, onAddToPipeline, height = 640 }: JobTableProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const columns = useMemo(
    () => [
      columnHelper.accessor((row) => row.job.title, {
        id: "title",
        header: "Poste",
        cell: (info) => {
          const job = info.row.original.job;
          return (
            <Box>
              <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: 320 }}>
                {job.title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {job.seniority ?? "—"} · {job.contract_type ?? "—"}
              </Typography>
            </Box>
          );
        },
      }),
      columnHelper.accessor((row) => row.job.remote_type ?? "", {
        id: "remote",
        header: "Remote",
        cell: (info) => {
          const value = info.getValue();
          return value ? <Chip size="small" variant="outlined" label={value} /> : "—";
        },
      }),
      columnHelper.accessor((row) => row.job.rate_eur_normalized ?? "0", {
        id: "rate",
        header: "TJM",
        cell: (info) => <Typography variant="body2">{formatRate(info.row.original.job)}</Typography>,
      }),
      columnHelper.accessor((row) => row.job.risk_score, {
        id: "risk",
        header: "Risque",
        cell: (info) => (
          <RiskBadge score={info.row.original.job.risk_score} reasons={info.row.original.job.risk_reasons} />
        ),
      }),
      columnHelper.display({
        id: "match",
        header: "Match",
        cell: (info) => {
          const row = info.row.original;
          return row.score !== undefined ? (
            <MatchScoreChip score={row.score} breakdown={row.breakdown} />
          ) : (
            "—"
          );
        },
      }),
      columnHelper.accessor((row) => row.job.detected_at, {
        id: "detected",
        header: "Detecte",
        cell: (info) => <Typography variant="body2">{formatDate(info.getValue())}</Typography>,
      }),
      columnHelper.display({
        id: "actions",
        header: "",
        cell: (info) => (
          <Tooltip title="Ajouter au pipeline">
            <span>
              <IconButton
                size="small"
                onClick={(event) => {
                  event.stopPropagation();
                  onAddToPipeline?.(info.row.original.job);
                }}
                disabled={!onAddToPipeline}
                aria-label="Ajouter au pipeline"
              >
                <AddTaskIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        ),
      }),
    ],
    [onAddToPipeline],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const tableRows = table.getRowModel().rows;

  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  const virtualRows = virtualizer.getVirtualItems();
  const totalSize = virtualizer.getTotalSize();
  const paddingTop = virtualRows.length > 0 ? virtualRows[0].start : 0;
  const paddingBottom = virtualRows.length > 0 ? totalSize - virtualRows[virtualRows.length - 1].end : 0;

  return (
    <Box
      ref={parentRef}
      sx={{
        height,
        overflow: "auto",
        border: "1px solid #e5e7eb",
        borderRadius: 1,
      }}
      role="table"
      aria-label="Liste des offres"
    >
      <Box component="table" sx={{ width: "100%", borderCollapse: "collapse" }}>
        <Box component="thead" sx={{ position: "sticky", top: 0, bgcolor: "background.paper", zIndex: 1 }}>
          {table.getHeaderGroups().map((headerGroup) => (
            <Box component="tr" key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Box
                  component="th"
                  key={header.id}
                  sx={{
                    textAlign: "left",
                    p: 1.25,
                    fontSize: 12,
                    color: "text.secondary",
                    borderBottom: "1px solid #e5e7eb",
                  }}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </Box>
              ))}
            </Box>
          ))}
        </Box>
        <Box component="tbody">
          {paddingTop > 0 && (
            <tr>
              <td colSpan={columns.length} style={{ height: paddingTop }} />
            </tr>
          )}
          {virtualRows.map((virtualRow) => {
            const row = tableRows[virtualRow.index];
            return (
              <Box
                component="tr"
                key={row.id}
                onClick={() => navigate(`/jobs/${row.original.job.id}`)}
                sx={{
                  cursor: "pointer",
                  "&:hover": { bgcolor: "action.hover" },
                  "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main" },
                }}
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter") navigate(`/jobs/${row.original.job.id}`);
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <Box
                    component="td"
                    key={cell.id}
                    sx={{ p: 1.25, borderBottom: "1px solid #f0f1f3", verticalAlign: "middle" }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </Box>
                ))}
              </Box>
            );
          })}
          {paddingBottom > 0 && (
            <tr>
              <td colSpan={columns.length} style={{ height: paddingBottom }} />
            </tr>
          )}
        </Box>
      </Box>
    </Box>
  );
}
