"use client";

import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { useController } from "react-hook-form";
import { Input, type InputProps } from "@/components/base/input/input";

interface FormInputProps<TFieldValues extends FieldValues>
  extends Omit<InputProps, "value" | "onChange" | "onBlur" | "name" | "ref"> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
}

/** Bridges react-hook-form (DOM-event based) with Untitled UI's React Aria
 * Input (value-callback based: `onChange(value: string)`, not an event). */
export function FormInput<TFieldValues extends FieldValues>({
  control,
  name,
  hint,
  ...props
}: FormInputProps<TFieldValues>) {
  const {
    field: { name: fieldName, value, onChange, onBlur, ref },
    fieldState,
  } = useController({ control, name });

  return (
    <Input
      {...props}
      name={fieldName}
      value={(value as string) ?? ""}
      onChange={onChange}
      onBlur={onBlur}
      ref={ref}
      isInvalid={!!fieldState.error}
      hint={fieldState.error?.message ?? hint}
    />
  );
}
