type NoticeProps = { value: string | null };

export function Notice({ value }: NoticeProps) {
  return value ? <p className="notice" role="status">{value}</p> : null;
}
