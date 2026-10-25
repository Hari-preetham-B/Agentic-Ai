"use client";

import { motion } from "framer-motion";

export const sectionVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6 },
  },
};

export const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.5 },
  },
};

interface SectionProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function Section({ children, className, delay = 0 }: SectionProps) {
  return (
    <motion.div
      className={className}
      variants={sectionVariants}
      initial="hidden"
      animate="visible"
      transition={{ delay }}
    >
      {children}
    </motion.div>
  );
}
