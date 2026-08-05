import { Toaster as Sonner, type ToasterProps } from 'sonner';

const Toaster = ({ ...props }: ToasterProps) => {
  return <Sonner theme="light" className="toaster group" position="top-right" richColors closeButton {...props} />;
};

export { Toaster };