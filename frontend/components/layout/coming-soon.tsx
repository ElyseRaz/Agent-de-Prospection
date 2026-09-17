import { Construction } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function ComingSoon({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <Construction className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Cet ecran arrive dans la {phase}.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
