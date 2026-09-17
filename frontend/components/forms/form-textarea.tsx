"use client";

import type { ComponentProps } from "react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { useController } from "react-hook-form";
import { TextArea } from "@/components/base/textarea/textarea";

type TextAreaProps = ComponentProps<typeof TextArea>;

interface FormTextAreaProps<TFieldValues extends FieldValues>
  extends Omit<TextAreaProps, "value" | "onChange" | "onBlur" | "name" | "ref" | "textAreaRef"> {
  control: Control<TFieldValues>;
  name: FieldPath<TFieldValues>;
}

/** Bridges react-hook-form with Untitled UI's React Aria TextArea (value-callback onChange). */
export function FormTextArea<TFieldValues extends FieldValues>({
  control,
  name,
  hint,
  ...props
}: FormTextAreaProps<TFieldValues>) {
  const { field, fieldState } = useController({ control, name });

  return (
    <TextArea
      {...props}
      name={field.name}
      value={(field.value as string) ?? ""}
      onChange={field.onChange}
      onBlur={field.onBlur}
      textAreaRef={field.ref}
      isInvalid={!!fieldState.error}
      hint={fieldState.error?.message ?? hint}
    />
  );
}
