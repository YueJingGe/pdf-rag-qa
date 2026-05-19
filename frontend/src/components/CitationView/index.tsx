import React from 'react';
import { Collapse, Tag, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import type { Citation } from '../../services/api';
import styles from './index.module.less';

export interface CitationClickInfo {
  filename: string;
  page: number;
  snippet: string;
}

interface Props {
  citations: Citation[];
  onCitationClick?: (info: CitationClickInfo) => void;
}

function formatFilename(rawFilename: string): string {
  // Remove UUID prefix like "3649288372a7442b82d21a26bd305122_"
  const uuidPrefixPattern = /^[a-f0-9]{32}_/;
  let name = rawFilename.replace(uuidPrefixPattern, '');
  // Remove _full1 suffix patterns
  name = name.replace(/_full\d+/, '');
  return name;
}

export default function CitationView({ citations, onCitationClick }: Props) {
  if (!citations.length) return null;

  return (
    <div className={styles.container}>
      <Collapse
        size="small"
        items={[
          {
            key: 'citations',
            label: (
              <span>
                <FileTextOutlined style={{ marginRight: 6 }} />
                引用来源（{citations.length}）
              </span>
            ),
            children: (
              <div className={styles.list}>
                {citations.map((citation, index) => (
                  <div
                    key={index}
                    className={`${styles.item} ${onCitationClick ? styles.clickable : ''}`}
                    onClick={() => onCitationClick?.({ filename: citation.filename, page: citation.page, snippet: citation.snippet })}
                  >
                    <div className={styles.meta}>
                      <Tag color="blue" className={styles.filenameTag}>
                        📄 {formatFilename(citation.filename)}
                      </Tag>
                      <Tag color="geekblue">第 {citation.page} 页</Tag>
                    </div>
                    <div className={styles.snippetLabel}>相关段落：</div>
                    <Typography.Paragraph
                      ellipsis={{ rows: 4, expandable: true, symbol: '展开全文' }}
                      className={styles.snippet}
                    >
                      {citation.snippet}
                    </Typography.Paragraph>
                  </div>
                ))}
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
